# Gate Project System

A comprehensive security gate control system using facial recognition, alarm management, and remote control capabilities via Telegram integration.

## 🚀 Features

- **Facial Recognition**: Automatic identification of authorized personnel using OpenCV and face_recognition
- **Multi-language Support**: English, Italian, Hebrew, and Russian translations
- **Telegram Integration**: Real-time notifications with photos and remote gate control
- **Alarm System**: Day/Night mode alarm control via Shelly switches
- **Touchscreen Interface**: Full-screen password entry with timeout protection
- **Event Logging**: Complete audit trail of all access attempts and system events
- **Internet Connectivity Check**: Ensures system reliability before operations
- **Hardware Integration**: Direct control of gates and alarms via network-connected devices

## 🏗️ System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Camera        │    │  Main Controller │    │  Telegram Bot   │
│  (Face Recog)   │◄──►│     (gpp.py)     │◄──►│  (Notifications)│
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │
                              ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│  Touchscreen    │    │   SQLite DBs     │    │  Shelly Switches│
│  (Password UI)  │◄──►│  (People/Events) │    │  (Gate/Alarm)   │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## 📋 Prerequisites

### Hardware Requirements
- Raspberry Pi 4 or similar Linux system
- USB Camera or Raspberry Pi Camera
- Touchscreen display
- Shelly 1 Plus switches for gate and alarm control
- Network connectivity

### Software Dependencies
```bash
# Python packages
pip install opencv-python
pip install face-recognition
pip install pygame
pip install pandas
pip install requests
pip install Pillow
pip install numpy

# System packages (Ubuntu/Debian)
sudo apt-get update
sudo apt-get install python3-tk
sudo apt-get install libatlas-base-dev
sudo apt-get install wmctrl  # Optional: for window management on Linux
```

## 🛠️ Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/gate-project-system.git
   cd gate-project-system
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure the system**
   ```bash
   cp gpp.ini.example gpp.ini
   # Edit gpp.ini with your specific settings
   ```

4. **Set up databases**
   ```bash
   # Create people database and add authorized users
   # Create translation file for multi-language support
   ```

5. **Configure Telegram Bot**
   - Create a bot via @BotFather on Telegram
   - Add your bot token and chat ID to `gpp.ini`

## ⚙️ Configuration

### Main Configuration (`gpp.ini`)

```ini
[TelegramButtons]
TOKEN = "your_telegram_bot_token"
chat_id = "your_chat_id"
N_to_buttons = 30

[IP_adresses]
ip_arm = 192.168.2.93      # Day mode alarm IP
ip_night = 192.168.2.38    # Night mode alarm IP
ip_off = 192.168.2.37      # Alarm off IP
ip_gate = 192.168.2.141    # Gate control IP

[OpenGate]
gate_delay = 88
gate_open_short = 10
gate_wait_short = 15

[Time-Outs]
to_keyb = 20              # Keyboard timeout
timeout_state_update = 5
timeout_attempt = 10
```

### Database Setup

1. **People Database** (`people.db`)
   - Contains person records with face encodings
   - Stores passwords, languages, and personal information

2. **Events Database** (`events.db`)
   - Logs all system events with timestamps
   - Stores photos and action codes for audit purposes

## 🚀 Usage

### Starting the System
```bash
python3 gpp.py
```

### User Interaction Flow

1. **Face Detection**: System captures and analyzes faces
2. **Recognition**: Identifies known users or marks as "Stranger"
3. **Authentication**: 
   - Known users: Direct access or password entry
   - Unknown users: Password required
4. **Action Selection**:
   - Enter password to open gate
   - Use `*password` for alarm setup menu
   - Press "Ping Lev" for remote authorization
5. **Gate/Alarm Control**: System executes requested actions

### Special Codes

- **Standard Password**: Opens gate and disables alarm
- **\*Password**: Access alarm setup menu with options:
  - Set Alarm (Day Mode)
  - Set Alarm (Night Mode)
  - Switch Off Alarm
  - Cancel
- **\*\*\*000\*\*\***: Emergency exit code

## 📱 Telegram Integration

### Features
- Real-time photo notifications when someone approaches
- Remote gate control via inline buttons
- Multi-language notification support
- Timeout handling for security

### Bot Commands
The system automatically sends notifications with:
- Photo of the person at the gate
- "Open Gate" button for authorized access
- "Cancel" button to deny access
- 30-second timeout for responses

## 🔧 Hardware Integration

### Shelly 1 Plus Configuration
The system controls Shelly switches via HTTP API:
- **Gate Control**: Short pulses to trigger gate opening
- **Alarm System**: Different relays for day/night modes
- **Status Monitoring**: Feedback on operation success

### API Endpoints
```
POST http://[shelly_ip]/rpc/Switch.Set
{
  "id": 0,
  "on": true/false
}
```

## 🌍 Multi-language Support

Supported languages:
- **EN**: English (default)
- **IT**: Italian
- **HE**: Hebrew
- **RU**: Russian

Language is determined per user from database settings.

## 🔐 Security Features

- **Face Recognition**: Primary authentication method
- **Password Backup**: Secondary authentication
- **Attempt Limiting**: Maximum 3 password attempts
- **Event Logging**: Complete audit trail
- **Timeout Protection**: Automatic session termination
- **Internet Dependency**: Requires connectivity for Telegram features

## 📊 Monitoring and Logs

### Event Codes
- `1`: Correct password entry
- `2`: Remote authorization (Ping Lev - Approved)
- `3`: Remote authorization (Ping Lev - Denied)
- `4`: Remote authorization timeout
- `11`: Alarm set (Day mode)
- `12`: Alarm set (Night mode)
- `10`: Alarm disabled

### Database Queries
```sql
-- View recent events
SELECT date, time, name, surname, action_code FROM events 
ORDER BY date DESC, time DESC LIMIT 50;

-- Check authorized users
SELECT name, surname, language FROM persons;
```

## 🛠️ Troubleshooting

### Common Issues

1. **Camera not detected**
   ```bash
   # Check camera permissions
   sudo usermod -a -G video $USER
   # Restart system
   ```

2. **Face recognition accuracy**
   - Ensure good lighting conditions
   - Add multiple photos per person to database
   - Check camera positioning and angle

3. **Network connectivity**
   - Verify Shelly device IP addresses
   - Test internet connection for Telegram
   - Check firewall settings

4. **Display issues**
   - Ensure proper display drivers
   - Check resolution settings
   - Verify fullscreen capabilities

## 🔄 Version History

- **v1.6**: Class FullScreenMessage moved to separate module
- **v1.5.1**: Fixed translation sequence for proper language display
- **v1.5**: Moved translations to separate module with caching
- **v1.4**: Added fullscreen alarm setup and multi-language support
- **v1.3**: Fixed Russian and Hebrew translations
- **v1.2**: Fixed alarm setup screen display

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This system is designed for educational and personal use. Ensure compliance with local privacy laws and regulations when implementing facial recognition systems. The authors are not responsible for any misuse or legal issues arising from the use of this software.

## 📞 Support

For support and questions:
- Create an issue in this repository
- Check the troubleshooting section above
- Review the configuration examples

---

**Note**: This system requires careful setup and testing before deployment in a production environment. Always test all components thoroughly and ensure proper backup procedures are in place.
