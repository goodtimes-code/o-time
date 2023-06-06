# o-time!
You can run a great timeline-based multimedia show (lasershow, lightshow,...) with *o-time!*, firing all your media clips with optional effects at the right time. Should work on all operating systems (Windows, MacOS, Linux) thanks to Python programming language.

# Demo
Watch a demo video here: https://youtu.be/FjxbE_0uRM8

# Technical features
- Media types
    - Laser
        - Multiple output devices (DACs) supported
        - Support for Helios DAC built-in
        - Laser objects:
            - Line
            - Circle
            - Wave (static and moving)
            - SVG
    - Configuration parameters:
        - Blank point frames
        - Interpolated points
        - Intensity
    - Transformation parameters:
        - X/Y axis shift
        - Color (R, G, B)
        - Rotation angle
        - Visible dots
        - Size
 - Audio
    - MP3
        - Configuration parameters:
            - Path
            - Volume

# How to use
Install requirements:
- Python3 (developed with Python 3.9 on MacOS)
- Python modules: `pip3 install -r requirements.txt`

Start server:
`./start_server.sh` or start a Redis server instance on your own.

Start preview:
Run `./start.sh` to see the laser preview window.
Hit key `p` to start playback of the timeline.

# Configuration
Edit 'config.json' in your favourite text editor.

# Web GUI
- Start web GUI to see the clip timeline in a graphical manner:
    - Run `cd core_webgui`
    - Run `./start.sh`
    - Open http://localhost:5000 in your favourite browser.

# Build your own plugin
You may provide new plugins to support more output types (like DMX, ArtNet, video playback, more laser DACs...).

Contact service@goodtimes.technology for custom commercial features.

Have a look at the very simple built-in audio receiver plugin in 'clip_receivers/core_audio/receiver.py'. The play() and stop() method will be fired automatically at the given playback time.

Add your customer receiver (ideas: ArtNet/DMX output, video playback,...) with this file structure:
- clip_receivers
    - <plugin_name>
        receiver.py

Add your new reciever to the 'receivers' section within config.json to make it startup automatically.
Add a new clip to 'config.json' to send clip events at the given time to your custom reciever name.

# Known limitations (How you can contribute)
- general:
    - No installers -> build and release installation package for each operating system
- core_webgui:
    - Configurations is done via text editor only ("config.json"). The webbased GUI is readonly -> Build a visual editor
- core_laser_group:
    - Flickering output when using multiple complex laser objects -> optimize paths
    - Only support for Helios Laser DAC built-in -> implement other laser DACs like Showtacle Moncha, Pangolin FB3/FB4, EasyLase,...
    - laser_preview:
        - Just one laser preview window possible at the same time

# Support
Get help by the community for free or contact service@goodtimes.technology for commercial support plans.
