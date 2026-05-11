# AI Remove Background for GIMP 3.x

A powerful GIMP 3.x plugin that uses AI models to automatically remove backgrounds from images, with support for multiple AI models, custom backgrounds, and batch processing.

Compatible with **GIMP 3.0, 3.2, and later 3.x releases**.

## About

**AI Remove Background** is an open-source GIMP plugin developed by [Gideon DeHaan](https://gideondehaan.dev), a 13-year-old programmer passionate about making advanced image editing tools accessible to everyone.

This plugin integrates the popular `rembg` Python library with GIMP 3, providing professional-quality background removal directly within your favorite image editor.

## Features

- **Multiple AI Models**: Choose from 8 different models via a labeled dropdown:
  - **U2-Net** — General purpose background removal
  - **U2-Net Human Segmentation** — Optimized for human subjects
  - **U2-Net Cloth Segmentation** — Specialized for clothing/fashion
  - **U2-Net Lightweight** — Faster processing, lower memory usage
  - **Silueta** — High-quality silhouette extraction
  - **ISNet General Use** — Advanced model for general use
  - **ISNet Anime** — Optimized for anime/illustration style images
  - **SAM (Segment Anything)** — Versatile segmentation for complex scenes

- **Flexible Background Options** (dropdown selector):
  - Transparent background (default)
  - White background
  - Black background
  - Custom color background (hex colors with optional alpha)

- **Advanced Features**:
  - Alpha matting for smoother edges (toggle enables/disables erode size control)
  - Optional layer mask creation
  - Square canvas resizing (centers and pads the image)
  - Batch processing for all open images at once
  - Preserves layer offsets and positioning

## Requirements

- **GIMP 3.0** or newer (tested on 3.0.x and 3.2.x)
- **Python 3.8+** with `rembg` installed
- **System**: Linux, macOS, or Windows

## Quick Install

On Linux or macOS, run the included install script:

```bash
chmod +x install.sh
./install.sh
```

This will set up the rembg virtual environment (if needed) and install the plugin into your GIMP plug-ins directory.

## Manual Installation

### Step 1: Install rembg

The plugin needs the `rembg` Python package. By default it looks for `~/.rembg/bin/python`:

```bash
python3 -m venv ~/.rembg
~/.rembg/bin/pip install rembg
```

### Step 2: Install the Plugin

1. **Find your GIMP plug-ins directory**:
   - **Linux**: `~/.config/GIMP/3.0/plug-ins/`
   - **macOS**: `~/Library/Application Support/GIMP/3.0/plug-ins/`
   - **Windows**: `%APPDATA%\GIMP\3.0\plug-ins\`

   If you have GIMP 3.2 installed, the path may use `3.2` instead of `3.0`.

2. **Create a plugin directory and copy the file**:
   ```bash
   mkdir -p ~/.config/GIMP/3.0/plug-ins/ai-remove-background-g3
   cp ai-remove-background-g3.py ~/.config/GIMP/3.0/plug-ins/ai-remove-background-g3/
   chmod +x ~/.config/GIMP/3.0/plug-ins/ai-remove-background-g3/ai-remove-background-g3.py
   ```

3. **Restart GIMP**

The plugin will appear under **Filters > AI > AI Remove Background...**

## Usage

1. Open an image in GIMP
2. Select the layer you want to process
3. Go to **Filters > AI > AI Remove Background...**
4. Configure your options:
   - **AI Model**: Choose the model best suited for your image
   - **Alpha Matting**: Check to enable smoother edges; adjusts the erode size slider
   - **Background**: Select transparent, white, black, or custom color
   - **Custom Color**: Enter a hex color when using Custom background
   - **Create Layer Mask**: Optionally attach a mask to the result layer
   - **Square Canvas**: Resize canvas to a centered square
   - **Process All Open Images**: Apply to every open image in batch
5. Click **OK** to process

### Tips for Best Results

- **Human portraits**: Use U2-Net Human Segmentation
- **Product photography**: Use ISNet General Use or U2-Net
- **Clothing/fashion**: Use U2-Net Cloth Segmentation
- **Anime/illustrations**: Use ISNet Anime
- **Complex scenes**: Try SAM with alpha matting enabled

## Troubleshooting

### Plugin doesn't appear in menu
- Ensure the plugin file is executable (`chmod +x`)
- Check that the plugin is in its own directory: `ai-remove-background-g3/ai-remove-background-g3.py`
- Verify GIMP version is 3.0 or newer
- Check GIMP's Error Console (Windows > Dockable Dialogs > Error Console)

### "Python executable not found" error
- Install rembg in the default location: `~/.rembg/bin/python`
- Or specify a custom Python path in the plugin dialog
- Verify rembg is installed: `~/.rembg/bin/python -m rembg.cli --help`

### "rembg failed" error
- Check that rembg is properly installed with all dependencies
- Some models download on first use — ensure you have internet access
- Check available disk space for model downloads (~100-500MB per model)

### Poor quality results
- Try different AI models — each is optimized for different image types
- Enable Alpha Matting for smoother edges
- Adjust the erode size (default: 15)
- Ensure your input image has good contrast between subject and background

## Advanced Configuration

### Using a Different Python Installation

Specify the path in the plugin dialog's "Python Path" field. Examples:
- Conda: `/home/user/miniconda3/envs/myenv/bin/python`
- System Python: `/usr/bin/python3`
- Virtual environment: `/path/to/venv/bin/python`

### Batch Processing

Enable "Process All Open Images" to apply the same settings to every open image at once. Useful for product photography, portrait sessions, and creating consistent assets.

### Custom Background Colors

When using Custom background mode, specify colors as:
- `#RRGGBB` — e.g., `#FF5733`
- `#RRGGBBAA` — with alpha, e.g., `#FF5733CC`

## License

This plugin is released under the **MIT License**.

```
MIT License

Copyright (c) 2025 Gideon DeHaan

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

## Contributing

Contributions are welcome! Feel free to:
- Report bugs or request features via GitHub Issues
- Submit pull requests with improvements
- Share your experience and help others in discussions

## Acknowledgments

- Built on top of the excellent [rembg](https://github.com/danielgatis/rembg) library
- Thanks to the GIMP development team for GIMP 3's improved Python API

## Technical Notes

- The plugin exports your selected layer as a temporary JPG file (unique name per run)
- Processes it through rembg using the selected AI model
- Imports the result as a PNG with transparency
- Optionally adds backgrounds or creates layer masks
- All temporary files are automatically cleaned up

---

**Made with love by [Gideon DeHaan](https://gideondehaan.dev)**
