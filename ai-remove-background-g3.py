#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import subprocess
import tempfile

import gi
gi.require_version('Gimp', '3.0')
gi.require_version('GimpUi', '3.0')
gi.require_version('Gegl', '0.4')
from gi.repository import Gimp, GimpUi, Gegl, Gio, GLib, GObject

MODELS = (
    "u2net",
    "u2net_human_seg",
    "u2net_cloth_seg",
    "u2netp",
    "silueta",
    "isnet-general-use",
    "isnet-anime",
    "sam",
)

# Background modes
BG_TRANSPARENT = 0
BG_WHITE       = 1
BG_BLACK       = 2
BG_CUSTOM      = 3

DEFAULT_PYTHON = os.path.expanduser("~/.rembg/bin/python")
PLUGIN_PROC_NAME = "plug-in-ai-remove-background-g3"
MENU_PATH = "<Image>/Filters/AI/"

def _cleanup(*paths):
    for p in paths:
        try:
            if p and os.path.exists(p):
                os.remove(p)
        except Exception:
            pass

def _export_drawable_as_jpg(image: Gimp.Image, drawable: Gimp.Drawable, jpg_path: str):
    """Export a composite of ONLY the given drawable to a JPG file."""
    dup = image.duplicate()
    try:
        pos = image.get_item_position(drawable)
        layers = dup.get_layers()  # top -> bottom
        for i, L in enumerate(layers):
            L.set_visible(i == pos)
        dup.merge_visible_layers(Gimp.MergeType.CLIP_TO_IMAGE)

        jpg_file = Gio.File.new_for_path(jpg_path)
        Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, dup, jpg_file, None)
    finally:
        pass

def _run_rembg(python_exe: str, model: str, alpha_matting: bool, ae_value: int, in_path: str, out_path: str):
    python_exe = os.path.expanduser(python_exe or "python3")
    if not os.path.exists(python_exe):
        raise RuntimeError(f"Python executable not found: {python_exe}")

    cmd = [python_exe, "-m", "rembg.cli", "i", "-m", model]
    if alpha_matting:
        cmd += ["-a", "-ae", str(int(ae_value))]
    cmd += [in_path, out_path]

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=False)
    _, stderr = proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(stderr.decode("utf-8", errors="ignore") or "rembg failed")

def _parse_color_rgba(color_str: str):
    """
    Parse color string '#RRGGBB' or '#RRGGBBAA' (case-insensitive) into floats 0..1.
    Fallback to white if parse fails.
    """
    s = (color_str or "").strip().lstrip("#")
    try:
        if len(s) == 6:
            r = int(s[0:2], 16) / 255.0
            g = int(s[2:4], 16) / 255.0
            b = int(s[4:6], 16) / 255.0
            a = 1.0
        elif len(s) == 8:
            r = int(s[0:2], 16) / 255.0
            g = int(s[2:4], 16) / 255.0
            b = int(s[4:6], 16) / 255.0
            a = int(s[6:8], 16) / 255.0
        else:
            return (1.0, 1.0, 1.0, 1.0)
        return (r, g, b, a)
    except Exception:
        return (1.0, 1.0, 1.0, 1.0)

def _new_bg_layer(image: Gimp.Image, mode: int, color_str: str):
    """
    Create and return a background layer per mode.
    For Transparent mode this returns None (no background).
    """
    if mode == BG_TRANSPARENT:
        return None

    w, h = image.get_width(), image.get_height()
    bg = Gimp.Layer.new(
        image,
        "Background",
        w, h,
        Gimp.ImageType.RGBA_IMAGE if mode == BG_CUSTOM else Gimp.ImageType.RGB_IMAGE,
        100.0,
        Gimp.LayerMode.NORMAL,
    )
    image.insert_layer(bg, None, -1)

    if mode == BG_WHITE:
        bg.fill(Gimp.FillType.WHITE)
    elif mode == BG_BLACK:
        bg.fill(Gimp.FillType.BLACK)
    elif mode == BG_CUSTOM:
        # Fill with custom color via GEGL solid-color node
        r, g, b, a = _parse_color_rgba(color_str)
        # Build a tiny GEGL graph to paint a solid color on the bg buffer
        Gegl.init(None)
        graph = Gegl.Node()
        solid = graph.create_child("gegl:solid-color")
        solid.set_property("value", (r, g, b, a))
        out = graph.create_child("gegl:write-buffer")
        out.set_property("buffer", bg.get_buffer())
        solid.link(out)
        out.process()
        bg.get_buffer().flush()

    return bg

def _mask_enum_alpha_fallback():
    """
    Return an AddMaskType that initializes a mask from alpha if available.
    Fall back to ADD_WHITE if not exposed in this build.
    """
    for name in ("ADD_ALPHA", "ADD_ALPHA_CHANNEL", "ADD_FROM_ALPHA", "FROM_ALPHA"):
        if hasattr(Gimp.AddMaskType, name):
            return getattr(Gimp.AddMaskType, name)
    return getattr(Gimp.AddMaskType, "ADD_WHITE")  # safe fallback

def _insert_result_layer(image: Gimp.Image, png_path: str, offset_x: int, offset_y: int,
                         as_mask: bool, bg_mode: int, bg_color_str: str,
                         orig_layer: Gimp.Layer | None):
    """
    Insert the rembg result. If bg_mode == Transparent: keep alpha and don't merge.
    Else, create background, position cut-out above it, merge down.
    If as_mask is True, attach a mask to the new cut-out layer.
    """
    png_file = Gio.File.new_for_path(png_path)
    cutout = Gimp.file_load_layer(Gimp.RunMode.NONINTERACTIVE, image, png_file)
    image.insert_layer(cutout, None, 0)
    cutout.set_offsets(offset_x, offset_y)

    # Optionally add a mask to the cutout itself (not required for transparency)
    if as_mask:
        mt = _mask_enum_alpha_fallback()
        try:
            mask = cutout.create_mask(mt)
            cutout.add_mask(mask)
        except Exception:
            # As a last resort ensure no crash if enum is odd on this build
            pass

    # Remove the original source layer so the cutout replaces it
    if orig_layer is not None:
        try:
            image.remove_layer(orig_layer)
        except Exception:
            pass

    # Background handling
    if bg_mode == BG_TRANSPARENT:
        # Nothing else to do — keep layers separate and transparent
        return

    # Otherwise, create and fill background then merge down
    bg = _new_bg_layer(image, bg_mode, bg_color_str)
    # Make sure cutout is above bg
    image.raise_item_to_top(cutout)
    # Merge cutout onto background -> result single non-transparent layer
    image.merge_down(cutout, Gimp.MergeType.CLIP_TO_BOTTOM_LAYER)

def _get_drawable_for_image(img: Gimp.Image) -> Gimp.Drawable | None:
    get_sel = getattr(img, "get_selected_layers", None)
    if callable(get_sel):
        sel = get_sel()
        if sel:
            return sel[0]
    layers = img.get_layers()
    return layers[0] if layers else None

def _process_image(image: Gimp.Image,
                   drawable: Gimp.Drawable,
                   as_mask: bool,
                   sel_model: int,
                   alpha_matting: bool,
                   ae_value: int,
                   bg_mode: int,
                   bg_color: str,
                   make_square: bool,
                   python_exe: str):
    if drawable is None:
        return

    offs = drawable.get_offsets()
    if isinstance(offs, tuple):
        if len(offs) == 3:
            _, off_x, off_y = offs
        elif len(offs) == 2:
            off_x, off_y = offs
        else:
            off_x = off_y = 0
    else:
        off_x = off_y = 0

    tdir = tempfile.gettempdir()
    jpg_path = os.path.join(tdir, "Temp-gimp-0000.jpg")
    png_path = os.path.join(tdir, "Temp-gimp-0000.png")

    _cleanup(jpg_path, png_path)

    _export_drawable_as_jpg(image, drawable, jpg_path)
    _run_rembg(python_exe, MODELS[sel_model], alpha_matting, ae_value, jpg_path, png_path)

    if not os.path.exists(png_path):
        raise RuntimeError("Output PNG was not created by rembg.")

    _insert_result_layer(image, png_path, off_x, off_y, as_mask, bg_mode, bg_color,
                         drawable if True else None)  # remove original layer always

    if make_square:
        w = image.get_width()
        h = image.get_height()
        max_side = max(w, h)
        image.resize(max_side, max_side, (max_side - w) // 2, (max_side - h) // 2)

    # IMPORTANT: don't merge-visible at the end if Transparent background,
    # otherwise we'd bake the alpha away when someone adds a bg later.
    # For non-transparent cases we already merged cutout onto the bg.
    # So nothing else to do here.

    _cleanup(jpg_path, png_path)

class RemoveBG(Gimp.PlugIn):
    def do_query_procedures(self):
        return [PLUGIN_PROC_NAME]

    def do_create_procedure(self, name):
        if name != PLUGIN_PROC_NAME:
            return None

        proc = Gimp.ImageProcedure.new(self, name, Gimp.PDBProcType.PLUGIN, self.run, None)
        proc.set_image_types("*")
        proc.set_sensitivity_mask(Gimp.ProcedureSensitivityMask.DRAWABLE)

        proc.set_menu_label("AI Remove Background…")
        proc.add_menu_path(MENU_PATH)

        proc.set_documentation(
            "Remove image background using rembg; default leaves transparency; "
            "optional background fill (white/black/custom), optional square canvas, batch mode.",
            "Exports the chosen drawable to JPG, runs rembg, and imports the result.",
            name,
        )
        proc.set_attribution("Tech Archive (ported)", "GPLv3", "2025")

        proc.add_boolean_argument(
            "as-mask", "Use as Mask",
            "Attach a mask to the cut-out layer (optional; transparency works without this).",
            False, GObject.ParamFlags.READWRITE,
        )
        proc.add_int_argument(
            "sel-model", "Model index",
            "Which rembg model to use: 0=u2net, 1=u2net_human_seg, 2=u2net_cloth_seg, 3=u2netp, 4=silueta, 5=isnet-general-use, 6=isnet-anime, 7=sam.",
            0, len(MODELS) - 1, 0, GObject.ParamFlags.READWRITE,
        )
        proc.add_boolean_argument(
            "alpha-matting", "Alpha Matting",
            "Enable rembg alpha matting (-a).",
            False, GObject.ParamFlags.READWRITE,
        )
        proc.add_int_argument(
            "ae-value", "Alpha Matting Erode Size",
            "Erode size for alpha matting (-ae).",
            1, 100, 15, GObject.ParamFlags.READWRITE,
        )

        # Background options
        proc.add_int_argument(
            "bg-mode", "Background mode",
            "0=Transparent (default), 1=White, 2=Black, 3=Custom color (#RRGGBB or #RRGGBBAA).",
            0, 3, BG_TRANSPARENT, GObject.ParamFlags.READWRITE,
        )
        proc.add_string_argument(
            "bg-color", "Custom background color",
            "Used only when Background mode = 3 (Custom). Example: #112233 or #112233CC.",
            "#00000000", GObject.ParamFlags.READWRITE,
        )

        proc.add_boolean_argument(
            "make-square", "Make Square",
            "Resize canvas to a centered square after background removal.",
            False, GObject.ParamFlags.READWRITE,
        )
        proc.add_boolean_argument(
            "process-all-images", "Process all open images",
            "If enabled, apply to every open image; otherwise only the current one.",
            False, GObject.ParamFlags.READWRITE,
        )
        proc.add_string_argument(
            "python-exe", "Python executable for rembg",
            "Path to Python where rembg is installed (default is ~/.rembg/bin/python).",
            DEFAULT_PYTHON, GObject.ParamFlags.READWRITE,
        )
        return proc

    def run(self, procedure, run_mode, image, drawables, config, run_data):
        if len(drawables) != 1:
            msg = "This plug-in works with exactly one drawable."
            err = GLib.Error.new_literal(Gimp.PlugIn.error_quark(), msg, 0)
            return procedure.new_return_values(Gimp.PDBStatusType.CALLING_ERROR, err)
        drawable = drawables[0]

        if run_mode == Gimp.RunMode.INTERACTIVE:
            GimpUi.init("ai-remove-background-g3")
            dlg = GimpUi.ProcedureDialog.new(procedure, config, "AI Remove Background")
            dlg.fill(["as-mask", "sel-model", "alpha-matting", "ae-value",
                      "bg-mode", "bg-color",
                      "make-square", "process-all-images", "python-exe"])
            if not dlg.run():
                dlg.destroy()
                return procedure.new_return_values(Gimp.PDBStatusType.CANCEL, GLib.Error())
            dlg.destroy()

        as_mask       = config.get_property("as-mask")
        sel_model     = config.get_property("sel-model")
        alpha_matting = config.get_property("alpha-matting")
        ae_value      = config.get_property("ae-value")
        bg_mode       = config.get_property("bg-mode")
        bg_color      = config.get_property("bg-color")
        make_square   = config.get_property("make-square")
        do_all        = config.get_property("process-all-images")
        python_exe    = config.get_property("python-exe") or DEFAULT_PYTHON

        try:
            if do_all:
                for img in Gimp.get_images():
                    d = _get_drawable_for_image(img)
                    if d is None:
                        continue
                    img.undo_group_start()
                    try:
                        _process_image(img, d, as_mask, sel_model, alpha_matting, ae_value,
                                       bg_mode, bg_color, make_square, python_exe)
                    finally:
                        img.undo_group_end()
            else:
                image.undo_group_start()
                try:
                    _process_image(image, drawable, as_mask, sel_model, alpha_matting, ae_value,
                                   bg_mode, bg_color, make_square, python_exe)
                finally:
                    image.undo_group_end()

            Gimp.displays_flush()
            return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())

        except Exception as e:
            Gimp.message(f"AI Remove Background error:\n{e}")
            return procedure.new_return_values(
                Gimp.PDBStatusType.EXECUTION_ERROR,
                GLib.Error.new_literal(Gimp.PlugIn.error_quark(), str(e), 0)
            )

Gimp.main(RemoveBG.__gtype__, sys.argv)
