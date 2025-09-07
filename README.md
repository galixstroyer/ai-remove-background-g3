# AI Remove Background for GIMP 3.0

A powerful GIMP 3.0.4+ plugin that uses AI models to automatically remove backgrounds from images, with support for multiple AI models, custom backgrounds, and batch processing.

## About

**AI Remove Background** is an open-source GIMP plugin developed by [Gideon DeHaan](https://gideondehaan.dev), a 13-year-old programmer passionate about making advanced image editing tools accessible to everyone.

This plugin integrates the popular `rembg` Python library with GIMP 3.0, providing professional-quality background removal directly within your favorite image editor.

## Features

- **Multiple AI Models**: Choose from 8 different AI models optimized for various use cases:
  - `u2net` - General purpose background removal
  - `u2net_human_seg` - Optimized for human subjects
  - `u2net_cloth_seg` - Specialized for clothing/fashion
  - `u2netp` - Lightweight version for faster processing
  - `silueta` - High-quality silhouette extraction
  - `isnet-general-use` - Advanced model for general use
  - `isnet-anime` - Optimized for anime/illustration style images
  - `sam` - Segment Anything Model for versatile segmentation

- **Flexible Background Options**:
  - Transparent background (default)
  - White background
  - Black background
  - Custom color background (supports hex colors with alpha)

- **Advanced Features**:
  - Alpha matting for smoother edges
  - Optional layer mask creation
  - Square canvas resizing
  - Batch processing for multiple open images
  - Preserves layer offsets and positioning

## Requirements

- **GIMP 3.0.4** or newer
- **Python 3.8+** with the following packages:
  - `rembg` (install via pip)
  - `gi` (Python GObject Introspection - usually comes with GIMP)
- **System**: Linux, macOS, or Windows

## Installation

### Step 1: Install rembg

First, you need to install the `rembg` Python package. The plugin looks for it in `~/.rembg/bin/python` by default:

```bash
# Create a virtual environment (recommended)
python3 -m venv ~/.rembg
~/.rembg/bin/pip install rembg

# Or install globally (not recommended)
pip install rembg
```

### Step 2: Install the Plugin

1. **Download the plugin file**: `ai-remove-background-g3.py`

2. **Find your GIMP plugins directory**:
   - **Linux**: `~/.config/GIMP/3.0/plug-ins/`
   - **macOS**: `~/Library/Application Support/GIMP/3.0/plug-ins/`
   - **Windows**: `%APPDATA%\GIMP\3.0\plug-ins\`

3. **Create a plugin directory**:
   ```bash
   mkdir -p ~/.config/GIMP/3.0/plug-ins/ai-remove-background-g3
   ```

4. **Copy the plugin file**:
   ```bash
   cp ai-remove-background-g3.py ~/.config/GIMP/3.0/plug-ins/ai-remove-background-g3/
   ```

5. **Make the plugin executable** (Linux/macOS only):
   ```bash
   chmod +x ~/.config/GIMP/3.0/plug-ins/ai-remove-background-g3/ai-remove-background-g3.py
   ```

6. **Restart GIMP**

The plugin will appear in the menu under **Filters → AI → AI Remove Background…**

## Usage

1. Open an image in GIMP
2. Select the layer you want to process
3. Go to **Filters → AI → AI Remove Background…**
4. Configure your options:
   - **Model**: Choose the AI model best suited for your image
   - **Alpha Matting**: Enable for smoother edges (increases processing time)
   - **Background Mode**: Select transparent, white, black, or custom color
   - **Make Square**: Optionally resize canvas to square dimensions
   - **Process All Images**: Apply to all open images in batch mode
5. Click **OK** to process

### Tips for Best Results

- **Human portraits**: Use `u2net_human_seg` model
- **Product photography**: Use `isnet-general-use` or `u2net`
- **Clothing/fashion**: Use `u2net_cloth_seg`
- **Anime/illustrations**: Use `isnet-anime`
- **Complex scenes**: Try `sam` model with alpha matting enabled

## Troubleshooting

### Plugin doesn't appear in menu
- Ensure the plugin file is executable (Linux/macOS)
- Check that the plugin is in its own directory: `ai-remove-background-g3/ai-remove-background-g3.py`
- Verify GIMP version is 3.0.4 or newer
- Check GIMP's Error Console (Windows → Dockable Dialogs → Error Console)

### "Python executable not found" error
- Install rembg in the default location: `~/.rembg/bin/python`
- Or specify a custom Python path in the plugin dialog
- Ensure Python has rembg installed: `python -m pip list | grep rembg`

### "rembg failed" error
- Check that rembg is properly installed with all dependencies
- Try running rembg from command line to test: `python -m rembg.cli --help`
- Some models download on first use - ensure you have internet connection
- Check available disk space for model downloads (~100-500MB per model)

### Poor quality results
- Try different AI models - each is optimized for different image types
- Enable Alpha Matting for smoother edges
- Adjust the Alpha Matting Erode Size (default: 15)
- Ensure your input image has good contrast between subject and background

## Advanced Configuration

### Using a Different Python Installation

If you have rembg installed in a different Python environment, you can specify the path in the plugin dialog's "Python executable" field. Examples:
- Conda: `/home/user/miniconda3/envs/myenv/bin/python`
- System Python: `/usr/bin/python3`
- Virtual environment: `/path/to/venv/bin/python`

### Batch Processing

Enable "Process all open images" to apply the same background removal settings to multiple images at once. This is useful for:
- Product photography workflows
- Portrait sessions
- Creating consistent assets for games/websites

### Custom Background Colors

When using Custom background mode, you can specify colors in these formats:
- `#RRGGBB` - Standard hex color (e.g., `#FF5733`)
- `#RRGGBBAA` - Hex color with alpha channel (e.g., `#FF5733CC`)

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

## Support the Developer

If you find this plugin useful, please consider supporting Gideon's work:

🎁 **[Donate](https://gideondehaan.dev/donate)** - Help a young developer continue creating awesome tools!

## Contributing

Contributions are welcome! Feel free to:
- Report bugs or request features via GitHub Issues
- Submit pull requests with improvements
- Share your experience and help others in discussions

## Acknowledgments

- Built on top of the excellent [rembg](https://github.com/danielgatis/rembg) library
- Thanks to the GIMP development team for GIMP 3.0's improved Python API
- Inspired by the needs of digital artists and photographers worldwide

## Technical Notes

- The plugin exports your selected layer as a temporary JPG file
- Processes it through rembg using the selected AI model
- Imports the result as a PNG with transparency
- Optionally adds backgrounds or creates layer masks
- All temporary files are automatically cleaned up

---

**Made with ❤️ by [Gideon DeHaan](https://gideondehaan.dev)** - A 13-year-old programmer making professional tools accessible to everyone