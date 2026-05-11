#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# AI Remove Background for GIMP 3.x
# Compatible with GIMP 3.0, 3.2, and later 3.x releases.
#
# Copyright (c) 2025 Gideon DeHaan — MIT License
# https://gideondehaan.dev

import os
import sys
import subprocess
import tempfile
import uuid

import gi
gi.require_version('Gimp', '3.0')
gi.require_version('GimpUi', '3.0')
gi.require_version('Gegl', '0.4')
from gi.repository import Gimp, GimpUi, Gegl, Gio, GLib, GObject

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

PLUGIN_PROC_NAME = "plug-in-ai-remove-background-g3"
MENU_PATH = "<Image>/Filters/AI/"
DEFAULT_PYTHON = os.path.expanduser("~/.rembg/bin/python")

MODELS = (
    ("u2net",            "U2-Net — General Purpose"),
    ("u2net_human_seg",  "U2-Net — Human Segmentation"),
    ("u2net_cloth_seg",  "U2-Net — Cloth Segmentation"),
    ("u2netp",           "U2-Net — Lightweight / Fast"),
    ("silueta",          "Silueta"),
    ("isnet-general-use","ISNet — General Use"),
    ("isnet-anime",      "ISNet — Anime / Illustration"),
    ("sam",              "SAM — Segment Anything"),
)

BG_MODES = (
    ("transparent", "Transparent"),
    ("white",       "White"),
    ("black",       "Black"),
    ("custom",      "Custom Color"),
)

# Check whether Gimp.Choice is available (GIMP ≥ 3.0.2 / 3.2+).
# Older 3.0.0 builds may not have it, so we fall back to int arguments.
_HAS_CHOICE = hasattr(Gimp, "Choice")

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

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
        for i, layer in enumerate(dup.get_layers()):
            layer.set_visible(i == pos)
        dup.merge_visible_layers(Gimp.MergeType.CLIP_TO_IMAGE)
        Gimp.file_save(Gimp.RunMode.NONINTERACTIVE, dup,
                       Gio.File.new_for_path(jpg_path), None)
    finally:
        dup.delete()


def _run_rembg(python_exe: str, model: str, alpha_matting: bool,
               ae_value: int, in_path: str, out_path: str):
    python_exe = os.path.expanduser(python_exe or "python3")
    if not os.path.exists(python_exe):
        raise RuntimeError(
            f"Python executable not found: {python_exe}\n\n"
            "Install rembg with:\n"
            "  python3 -m venv ~/.rembg\n"
            "  ~/.rembg/bin/pip install rembg"
        )

    cmd = [python_exe, "-m", "rembg.cli", "i", "-m", model]
    if alpha_matting:
        cmd += ["-a", "-ae", str(int(ae_value))]
    cmd += [in_path, out_path]

    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE, shell=False)
    _, stderr = proc.communicate()
    if proc.returncode != 0:
        msg = stderr.decode("utf-8", errors="ignore").strip()
        raise RuntimeError(msg or "rembg exited with an error")


def _parse_color_rgba(color_str: str):
    """Parse '#RRGGBB' or '#RRGGBBAA' → (r, g, b, a) floats 0‥1."""
    s = (color_str or "").strip().lstrip("#")
    try:
        if len(s) == 6:
            return (int(s[0:2], 16) / 255.0,
                    int(s[2:4], 16) / 255.0,
                    int(s[4:6], 16) / 255.0, 1.0)
        if len(s) == 8:
            return (int(s[0:2], 16) / 255.0,
                    int(s[2:4], 16) / 255.0,
                    int(s[4:6], 16) / 255.0,
                    int(s[6:8], 16) / 255.0)
    except Exception:
        pass
    return (1.0, 1.0, 1.0, 1.0)


def _new_bg_layer(image: Gimp.Image, bg_mode: str, color_str: str):
    """Create a filled background layer.  Returns None for transparent."""
    if bg_mode == "transparent":
        return None

    w, h = image.get_width(), image.get_height()
    use_alpha = (bg_mode == "custom")
    bg = Gimp.Layer.new(
        image, "Background", w, h,
        Gimp.ImageType.RGBA_IMAGE if use_alpha else Gimp.ImageType.RGB_IMAGE,
        100.0, Gimp.LayerMode.NORMAL,
    )
    image.insert_layer(bg, None, -1)

    if bg_mode == "white":
        bg.fill(Gimp.FillType.WHITE)
    elif bg_mode == "black":
        bg.fill(Gimp.FillType.BLACK)
    elif bg_mode == "custom":
        r, g, b, a = _parse_color_rgba(color_str)
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


def _mask_enum_alpha():
    """Return the AddMaskType for 'from alpha', with cross-version fallback."""
    for name in ("ADD_ALPHA", "ADD_ALPHA_CHANNEL", "ADD_FROM_ALPHA", "FROM_ALPHA"):
        if hasattr(Gimp.AddMaskType, name):
            return getattr(Gimp.AddMaskType, name)
    return getattr(Gimp.AddMaskType, "ADD_WHITE")


def _insert_result_layer(image, png_path, off_x, off_y,
                         as_mask, bg_mode, bg_color, orig_layer):
    """Load the rembg output PNG and compose it into the image."""
    cutout = Gimp.file_load_layer(
        Gimp.RunMode.NONINTERACTIVE, image,
        Gio.File.new_for_path(png_path))
    image.insert_layer(cutout, None, 0)
    cutout.set_offsets(off_x, off_y)

    if as_mask:
        try:
            mask = cutout.create_mask(_mask_enum_alpha())
            cutout.add_mask(mask)
        except Exception:
            pass

    if orig_layer is not None:
        try:
            image.remove_layer(orig_layer)
        except Exception:
            pass

    if bg_mode == "transparent":
        return

    _new_bg_layer(image, bg_mode, bg_color)
    image.raise_item_to_top(cutout)
    image.merge_down(cutout, Gimp.MergeType.CLIP_TO_BOTTOM_LAYER)


def _get_drawable(img: Gimp.Image):
    sel = getattr(img, "get_selected_layers", None)
    if callable(sel):
        layers = sel()
        if layers:
            return layers[0]
    layers = img.get_layers()
    return layers[0] if layers else None


# ---------------------------------------------------------------------------
# Resolve model / bg-mode from config (works with Choice *or* int args)
# ---------------------------------------------------------------------------

def _resolve_model(config):
    """Return the model nick string regardless of argument type."""
    if _HAS_CHOICE:
        return config.get_property("model")
    idx = config.get_property("sel-model")
    return MODELS[min(idx, len(MODELS) - 1)][0]


def _resolve_bg_mode(config):
    """Return the bg-mode nick string regardless of argument type."""
    if _HAS_CHOICE:
        return config.get_property("bg-mode")
    idx = config.get_property("bg-mode-idx")
    return BG_MODES[min(idx, len(BG_MODES) - 1)][0]


# ---------------------------------------------------------------------------
# Core processing
# ---------------------------------------------------------------------------

def _process_image(image, drawable, as_mask, model, alpha_matting, ae_value,
                   bg_mode, bg_color, make_square, python_exe):
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

    uid = uuid.uuid4().hex[:8]
    tdir = tempfile.gettempdir()
    jpg_path = os.path.join(tdir, f"gimp-rembg-{uid}.jpg")
    png_path = os.path.join(tdir, f"gimp-rembg-{uid}.png")

    try:
        _export_drawable_as_jpg(image, drawable, jpg_path)
        _run_rembg(python_exe, model, alpha_matting, ae_value,
                   jpg_path, png_path)

        if not os.path.exists(png_path):
            raise RuntimeError("Output PNG was not created by rembg.")

        _insert_result_layer(image, png_path, off_x, off_y,
                             as_mask, bg_mode, bg_color, drawable)

        if make_square:
            w, h = image.get_width(), image.get_height()
            s = max(w, h)
            image.resize(s, s, (s - w) // 2, (s - h) // 2)
    finally:
        _cleanup(jpg_path, png_path)


# ---------------------------------------------------------------------------
# GIMP Plug-In class
# ---------------------------------------------------------------------------

class RemoveBG(Gimp.PlugIn):

    def do_query_procedures(self):
        return [PLUGIN_PROC_NAME]

    def do_create_procedure(self, name):
        if name != PLUGIN_PROC_NAME:
            return None

        proc = Gimp.ImageProcedure.new(
            self, name, Gimp.PDBProcType.PLUGIN, self.run, None)
        proc.set_image_types("*")
        proc.set_sensitivity_mask(Gimp.ProcedureSensitivityMask.DRAWABLE)

        proc.set_menu_label("AI Remove Background…")
        proc.add_menu_path(MENU_PATH)
        proc.set_documentation(
            "Remove image background using AI (rembg)",
            "Exports the selected layer, runs rembg AI background removal, "
            "and imports the result with optional background fill.",
            name,
        )
        proc.set_attribution("Gideon DeHaan", "MIT", "2025")

        # -- Model selection ------------------------------------------------
        if _HAS_CHOICE:
            model_choice = Gimp.Choice.new()
            for i, (nick, label) in enumerate(MODELS):
                model_choice.add(nick, i, label, "")
            proc.add_choice_argument(
                "model", "AI Model",
                "Select the AI model for background removal",
                model_choice, "u2net", GObject.ParamFlags.READWRITE,
            )
        else:
            desc = ", ".join(f"{i}={m[0]}" for i, m in enumerate(MODELS))
            proc.add_int_argument(
                "sel-model", "Model index", desc,
                0, len(MODELS) - 1, 0, GObject.ParamFlags.READWRITE,
            )

        # -- Alpha matting --------------------------------------------------
        proc.add_boolean_argument(
            "alpha-matting", "Alpha Matting",
            "Enable alpha matting for smoother edges",
            False, GObject.ParamFlags.READWRITE,
        )
        proc.add_int_argument(
            "ae-value", "Erode Size",
            "Alpha matting erode size (higher = more erosion at edges)",
            1, 100, 15, GObject.ParamFlags.READWRITE,
        )

        # -- Background -----------------------------------------------------
        if _HAS_CHOICE:
            bg_choice = Gimp.Choice.new()
            for i, (nick, label) in enumerate(BG_MODES):
                bg_choice.add(nick, i, label, "")
            proc.add_choice_argument(
                "bg-mode", "Background",
                "Background fill mode after removal",
                bg_choice, "transparent", GObject.ParamFlags.READWRITE,
            )
        else:
            desc = ", ".join(f"{i}={m[0]}" for i, m in enumerate(BG_MODES))
            proc.add_int_argument(
                "bg-mode-idx", "Background mode", desc,
                0, len(BG_MODES) - 1, 0, GObject.ParamFlags.READWRITE,
            )

        proc.add_string_argument(
            "bg-color", "Custom Color",
            "Hex color (#RRGGBB or #RRGGBBAA) — used only with Custom background",
            "#00000000", GObject.ParamFlags.READWRITE,
        )

        # -- Extra options --------------------------------------------------
        proc.add_boolean_argument(
            "as-mask", "Create Layer Mask",
            "Attach a layer mask from the alpha channel",
            False, GObject.ParamFlags.READWRITE,
        )
        proc.add_boolean_argument(
            "make-square", "Square Canvas",
            "Resize the canvas to a centered square after removal",
            False, GObject.ParamFlags.READWRITE,
        )
        proc.add_boolean_argument(
            "process-all", "Process All Open Images",
            "Apply background removal to every open image",
            False, GObject.ParamFlags.READWRITE,
        )
        proc.add_string_argument(
            "python-exe", "Python Path",
            "Path to the Python interpreter where rembg is installed",
            DEFAULT_PYTHON, GObject.ParamFlags.READWRITE,
        )

        return proc

    # -----------------------------------------------------------------------
    # Dialog & execution
    # -----------------------------------------------------------------------

    def run(self, procedure, run_mode, image, drawables, config, run_data):
        if len(drawables) != 1:
            err = GLib.Error.new_literal(
                Gimp.PlugIn.error_quark(),
                "Please select exactly one layer before running this plug-in.", 0)
            return procedure.new_return_values(
                Gimp.PDBStatusType.CALLING_ERROR, err)
        drawable = drawables[0]

        if run_mode == Gimp.RunMode.INTERACTIVE:
            GimpUi.init("ai-remove-background-g3")
            dlg = GimpUi.ProcedureDialog.new(
                procedure, config, "AI Remove Background")

            # Organise the dialog into logical sections.
            # Alpha-matting checkbox toggles sensitivity of erode-size.
            dlg.fill_frame("matting-frame", "alpha-matting", False, "ae-value")

            model_prop = "model" if _HAS_CHOICE else "sel-model"
            bg_prop    = "bg-mode" if _HAS_CHOICE else "bg-mode-idx"

            dlg.fill([model_prop, "matting-frame",
                      bg_prop, "bg-color",
                      "as-mask", "make-square", "process-all",
                      "python-exe"])

            if not dlg.run():
                dlg.destroy()
                return procedure.new_return_values(
                    Gimp.PDBStatusType.CANCEL, GLib.Error())
            dlg.destroy()

        model         = _resolve_model(config)
        bg_mode       = _resolve_bg_mode(config)
        alpha_matting = config.get_property("alpha-matting")
        ae_value      = config.get_property("ae-value")
        bg_color      = config.get_property("bg-color")
        as_mask       = config.get_property("as-mask")
        make_square   = config.get_property("make-square")
        do_all        = config.get_property("process-all")
        python_exe    = config.get_property("python-exe") or DEFAULT_PYTHON

        try:
            if do_all:
                for img in Gimp.get_images():
                    d = _get_drawable(img)
                    if d is None:
                        continue
                    img.undo_group_start()
                    try:
                        _process_image(img, d, as_mask, model, alpha_matting,
                                       ae_value, bg_mode, bg_color,
                                       make_square, python_exe)
                    finally:
                        img.undo_group_end()
            else:
                image.undo_group_start()
                try:
                    _process_image(image, drawable, as_mask, model,
                                   alpha_matting, ae_value, bg_mode,
                                   bg_color, make_square, python_exe)
                finally:
                    image.undo_group_end()

            Gimp.displays_flush()
            return procedure.new_return_values(
                Gimp.PDBStatusType.SUCCESS, GLib.Error())

        except Exception as e:
            Gimp.message(f"AI Remove Background error:\n{e}")
            return procedure.new_return_values(
                Gimp.PDBStatusType.EXECUTION_ERROR,
                GLib.Error.new_literal(Gimp.PlugIn.error_quark(), str(e), 0))


Gimp.main(RemoveBG.__gtype__, sys.argv)
