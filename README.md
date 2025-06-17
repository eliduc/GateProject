# Gate Project System

A facial recognition-based gate and alarm control system with Telegram integration and multi-language support.

## 🎯 Overview

Gate Project System is a comprehensive security solution that combines:
- Face recognition for automated access control
- PIN code authentication with on-screen keyboard
- Remote gate control via Telegram
- Alarm system management (Day/Night modes)
- Multi-language support (English, Italian, and more)
- Event logging with photo capture

## ✨ Features

### Security Features
- **Face Recognition**: Automatic identification of authorized persons
- **PIN Authentication**: Secure keypad with attempt limiting
- **Two-Factor Verification**: Option to require Telegram confirmation
- **Stranger Detection**: Alerts for unrecognized faces
- **Event Logging**: Complete audit trail with photos

### System Control
- **Gate Control**: Automated gate opening via Shelly relays
- **Alarm Management**: 
  - Day mode alarm
  - Night mode alarm
  - Remote alarm control
- **Telegram Integration**:
  - Real-time notifications with photos
  - Remote gate opening approval
  - Status updates

### User Experience
- **Multi-language Support**: Easy language switching per user
- **Fullscreen Interface**: Clean, distraction-free UI
- **Visual Feedback**: Clear status indicators and animations
- **Timeout Protection**: Automatic logout for security

## 📋 Requirements

### Hardware
- Raspberry Pi 4 (recommended) or any Linux/Windows PC
- USB Camera or Raspberry Pi Camera
- Display (touchscreen recommended)
- Shelly 1 Plus relays (for gate and alarm control)
- Internet connection (for Telegram features)

### Software Dependencies

#### System Packages (Ubuntu/Raspberry Pi)
```bash
sudo apt-get update
sudo apt-get install -y \
    python3-dev python3-pip \
    cmake build-essential \
    libopenblas-dev liblapack-dev \
    libjpeg-dev libpng-dev \
    libavcodec-dev libavformat-dev libswscale-dev \
    libgtk2.0-dev libgtk-3-dev \
    libatlas-base-dev gfortran \
    libboost-all-dev
```

#### Python Packages
```bash
pip3 install pygame
pip3 install opencv-python
pip3 install face-recognition
pip3 install pillow
pip3 install numpy
pip3 install requests
pip3 install pandas
pip3 install paramiko  # For database manager SSH connection
```

## 🚀 Installation

1. **Clone the repository**
```bash
git clone https://github.com/yourusername/gate-project-system.git
cd gate-project-system
```

2. **Install system dependencies**
```bash
sudo apt-get update
sudo apt-get install -y python3-dev python3-pip cmake build-essential
# ... (see full list above)
```

3. **Install Python packages**
```bash
pip3 install -r requirements.txt
```

4. **Configure the system**
- Edit `gpp.ini` with your settings
- Set up your Telegram bot token
- Configure IP addresses for Shelly devices

5. **Set up the database**
- Configure `config.json` for the database manager
- Run `python3 manageDB.py` to manage users
- Add authorized users with their photos for face recognition

## ⚙️ Configuration

### Main Configuration (gpp.ini - rename from gpp.template.ini)

```ini
[TelegramButtons]
TOKEN = "YOUR_TELEGRAM_BOT_TOKEN"
chat_id = "YOUR_CHAT_ID"
N_to_buttons = 30

[IP_adresses]
ip_arm = 192.168.2.93      # Day mode alarm
ip_night = 192.168.2.38    # Night mode alarm
ip_off = 192.168.2.37      # Alarm off
ip_gate = 192.168.2.141    # Gate control

[OpenGate]
gate_delay = 88            # Total gate operation time
gate_open_short = 10       # First opening duration
gate_wait_short = 15       # Wait between operations

[Time-Outs]
to_keyb = 20              # Keyboard timeout in seconds
```

### Telegram Setup

1. Create a bot using [@BotFather](https://t.me/botfather)
2. Get your bot token
3. Get your chat ID (send a message to your bot and check: `https://api.telegram.org/bot<YourBOTToken>/getUpdates`)
4. Update `gpp.ini` with your credentials

### Shelly Device Setup

1. Connect Shelly 1 Plus devices to your network
2. Note their IP addresses
3. Update the `[IP_adresses]` section in `gpp.ini`

## 🏃 Running the System

### Basic Usage
```bash
python3 gpp.py
```

### Auto-start on Boot (Raspberry Pi)
Add to `/etc/rc.local`:
```bash
cd /home/pi/GateProject && python3 gpp.py &
```

Or create a systemd service:
```ini
[Unit]
Description=Gate Project System
After=multi-user.target

[Service]
Type=simple
ExecStart=/usr/bin/python3 /home/pi/GateProject/gpp.py
Restart=on-failure
User=pi

[Install]
WantedBy=multi-user.target
```

## 💻 Usage Guide

### Face Recognition
1. Stand in front of the camera
2. Wait for face detection
3. System will recognize and greet you
4. Enter your PIN code when prompted

### PIN Entry
- Use on-screen keypad or physical keyboard
- Special codes:
  - `*[PIN]` - Opens alarm menu after correct PIN
  - `***000***` - System exit code

### Alarm Control
After entering `*[PIN]`:
1. **Set Alarm (Day Mode)** - Standard alarm activation
2. **Set Alarm (Night Mode)** - Enhanced security mode
3. **Switch Off Alarm** - Deactivate alarm
4. **Cancel** - Return to main screen

### Telegram Features
- **Ping Lev** button - Sends photo and request to Telegram
- Remote approval - Respond to Telegram message to open gate
- All events are logged with photos

## 📁 Project Structure

```
gate-project-system/
├── gpp.py                          # Main application
├── Alarm_On.py                     # Alarm activation module
├── Alarm_Off.py                    # Alarm deactivation module
├── ControlSwitch.py                # Shelly relay control
├── TelegramButtons.py              # Telegram integration
├── translations.py                 # Translation system
├── manageDB.py                     # Database management GUI
├── config.json                     # Database manager configuration
├── gpp.ini                         # Main configuration
├── gate_project_translations.md    # Translation strings
├── people.db                       # User database
├── events.db                       # Event log database
└── README.md                       # This file
```

## 🗄️ Database Management

### Using the Database Manager (manageDB.py)

The system includes a graphical database management tool for easy user administration.

#### Setup
1. Rename 'config.template.json' and  configure `config.json` with your Raspberry Pi connection details:
```json
{
    "rpi_host": "rpi IP address",
    "rpi_port": 22,
    "rpi_user": "user name",
    "rpi_password": "password",
    "db_faces_path": "/home/pi/GateProject/people.db",
    "sqlite_path": "/usr/bin/sqlite3"
}
```

2. Install additional dependencies:
```bash
pip3 install paramiko
```

#### Running the Database Manager
```bash
python3 manageDB.py
```

#### Features
- **View Users**: Browse all registered persons with their photos
- **Add Users**: 
  - Enter name, surname, language (EN/IT/RU/HB/NA), and PIN
  - Capture photos directly from camera
  - Password is automatically hashed using SHA256
- **Edit Users**: Modify user details and passwords
- **Delete Users**: Remove users and all associated photos
- **Photo Management**:
  - Add single photos or bulk import from directory
  - View photo thumbnails with navigation
  - Delete individual photos
  - Remove duplicate photos automatically
  - Maximum 20 photos per person

#### Workflow
1. The tool downloads `people.db` from the Raspberry Pi on startup
2. Make your changes using the GUI
3. On exit, choose to save changes:
   - Updates local `people.db`
   - Uploads to Raspberry Pi automatically

#### Password Management
Passwords are automatically hashed using SHA256. When editing a user:
- Leave the password field unchanged to keep the existing password
- Enter a new password to update it

### Manual Password Hash Generation
If you need to generate a password hash manually:
```python
import hashlib
password = "1234"
hash = hashlib.sha256(password.encode()).hexdigest()
print(hash)
```

## 🌐 Multi-language Support

Languages are stored in `gate_project_translations.md`:
```markdown
Phrase ID|EN|IT
---|---|---
1|Welcome to Gate System|Benvenuto al sistema cancello
15|Enter the code|Inserisci il codice
...
```

Each user can have their preferred language set in the database.

## 🔧 Troubleshooting

### Camera Issues
- Check camera connection: `ls /dev/video*`
- Test camera: `raspistill -o test.jpg` (Raspberry Pi)
- Ensure proper permissions: `sudo usermod -a -G video $USER`

### Face Recognition Issues
- Ensure good lighting
- Add multiple photos per person from different angles
- Check face encoding cache files exist
- Delete cache files to force rebuild

### Display Issues
- Set DISPLAY variable: `export DISPLAY=:0`
- Check pygame can access display
- For headless operation, use virtual display

### Performance Optimization
- Face encoding cache improves startup time
- Reduce camera resolution if needed
- Use HOG model for faster detection

### Database Manager Issues
- **SSH Connection Failed**: Check `config.json` settings and network connectivity
- **Permission Denied**: Ensure the Pi user has read/write access to the database files
- **Camera Not Working**: Install `python3-tk` for camera support in the GUI
- **Photos Not Displaying**: Check that `pillow` is properly installed

## 🛡️ Security Considerations

1. **Physical Security**
   - Mount camera at appropriate height
   - Protect Raspberry Pi in weatherproof enclosure
   - Secure all network connections

2. **Network Security**
   - Use strong WiFi passwords
   - Consider VPN for remote access
   - Keep system updated

3. **Access Control**
   - Regular review of authorized users
   - Strong PIN requirements
   - Monitor event logs

## 📝 Event Codes

- `1` - Successful gate opening (PIN)
- `2` - Gate opened via Telegram approval
- `3` - Telegram request denied
- `4` - Telegram timeout or error
- `10` - Alarm turned off
- `11` - Alarm set (Day mode)
- `12` - Alarm set (Night mode)
- `-1` - Cancelled operation
- `-2` - Failed authentication/timeout

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Face recognition powered by [face_recognition](https://github.com/ageitgey/face_recognition)
- UI built with [Pygame](https://www.pygame.org/)
- Relay control via [Shelly](https://www.shelly.cloud/) devices

## 📧 Support

For issues and questions:
- Create an issue on GitHub
- Check existing issues for solutions
- Review logs in `events.db` for troubleshooting

---

**Version**: 2.0.0  
**Last Updated**: 2025