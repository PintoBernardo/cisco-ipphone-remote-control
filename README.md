# 📞 Cisco Multi-Model Remote Control Suite

A **high‑fidelity remote management workstation** for Cisco IP Phones.
This tool enables Network & UC Engineers to perform **“Remote Hands” operations** on Cisco phones using a virtualized hardware interface, featuring **live screen mirroring** and **XML‑CGI command execution**.

Designed for **enterprise, lab, and data‑center environments** where physical access to phones is limited or impossible.

---

## ✨ Key Features

* 📱 Virtual Cisco Phone UI (88xx & 79xx series)
* 🖥️ Live screen capture (PNG/BMP rendering)
* 🔘 Full button emulation via XML‑CGI
* 🔐 SSH bridge (jump‑host support)
* ⚡ Low‑latency background refresh
* 🧾 Live CURL command & response logs
* 💾 Session presets (IP lists)

---

## 🏗️ Architecture Overview

The application acts as a **secure middle‑man** between the engineer and Cisco IP Phone services.

### Core Components

* **CiscoBasePhone**

  * Handles authentication, networking, CGI execution, and image fetching

* **Model‑Specific Classes**

  * Define button layouts and supported keys per phone model

* **JSON‑Driven Configuration**

  * Button behavior is fully externalized and model‑agnostic

### Data Flow

1. **User Input**
   Clicks a button on the virtual phone UI

2. **Payload Mapping**
   Button → CGI URI (example: `Key:Soft1`)

3. **Transport Layer**

   * **Direct Mode:** Local `curl` execution
   * **SSH Bridge Mode:** `paramiko` executes curl via jump host

4. **Rendering**

   * Phone returns PNG/BMP image
   * Processed with **Pillow**
   * Rendered on **Tkinter canvas**

---

## 📂 Configuration & Data Migration (CRITICAL)

> ⚠️ **Buttons will NOT function without the correct JSON mappings**

The application separates:

* **Logic** → Python source
* **Behavior** → External JSON files

### Required Directory (EXE Mode)

When running as a standalone executable, key mappings must exist in:

```
%APPDATA%\CGI_Remote_Control\
```

### Mandatory Files

```
keys_8841.json
keys_7945.json
keys_7911.json
```

### Manual Setup Steps

1. Open the source directory:

   ```
   config/
   ```

2. Select **only the files**, not the folder

3. Copy them to:

   ```
   %APPDATA%\CGI_Remote_Control\
   ```

✅ Once present, all buttons will map correctly.

---

## 🛠️ Prerequisites

### System Requirements

#### curl (MANDATORY)

The application relies on `curl` for HTTP communication with Cisco phones.

* Must be installed
* Must be available in **PATH**

Verify:

```bash
curl --version
```

❌ If this fails, command execution and screen capture will not work.

---

### Cisco Phone / CUCM Requirements

* **Web Access:** Enabled
* **Settings Access:** Enabled
* **Authentication URL:** Valid XML authentication service
* **Permissions:**

  * Phone associated with an **Application User**
  * User is member of:

    ```
    Standard CTI Allow Control of Phones
    ```

---

## 🚀 Development & Deployment

### Python Dependencies

```bash
pip install pillow paramiko
```

---

## 📦 Building the Standalone Executable

Use the following **verified PyInstaller command**:

```bash
pyinstaller --noconfirm --onefile --windowed \
--name "CiscoRemoteControl" \
--icon="icon.ico" \
--add-data "icon.ico;." \
--add-data "cisco_core.py;." \
--add-data "cisco_8841.py;." \
--add-data "cisco_7911.py;." \
--add-data "cisco_7945.py;." \
--add-data "config/cgi.conf;config" \
--add-data "config/keys_7911.json;config" \
--add-data "config/keys_7945.json;config" \
--add-data "config/keys_8841.json;config" \
--add-data "config/sessions.json;config" \
--add-data "config/ssh.conf;config" \
main.py
```

---

## ⚙️ Feature Breakdown

### 🔐 SSH Bridge Mode

Control phones inside secured networks **without direct VPN access**.

### 🧾 Live Logs

Real‑time visibility of:

* Executed CURL commands
* Raw XML / HTTP responses

### 💾 Session Presets

Save and reload IP lists to eliminate repetitive typing.

### ⚡ Optimized Performance

Threaded background image fetching for smooth UI updates.

---

## 📝 Project Summary

**Cisco Multi‑Model Remote Control Suite** virtualizes the physical interface of Cisco **88xx and 79xx IP Phones**, enabling:

* Remote troubleshooting
* User assistance & training
* Status verification
* Secure data‑center operations

With **SSH tunneling**, **live CGI execution**, and **accurate UI emulation**, it provides a powerful alternative to physical access and traditional CUCM workflows.

---

## ⚠️ Disclaimer

This tool is intended **for administrative and engineering use only**.

Ensure compliance with:

* Organizational security policies
* Cisco licensing terms
* Local privacy and monitoring regulations
