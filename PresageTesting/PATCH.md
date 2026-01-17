# SmartSpectra SDK Patches for Ubuntu 22.04

This document describes the patches and workarounds needed to successfully compile the SmartSpectra C++ SDK examples on Ubuntu 22.04 (Jammy).

## Issue: GLES3 Detection Failure

The SmartSpectra SDK 2.0.4 was built with a requirement for `OpenGL::GLES3`, but CMake 3.22 (included with Ubuntu 22.04) cannot properly detect GLES3 as a component. On Ubuntu 22.04, GLES3 functionality is provided through the GLESv2 library.

## Required Patches

### 1. Patch SmartSpectra CMake Configuration

Edit `/usr/local/lib/cmake/SmartSpectra/SmartSpectraConfig.cmake`:

**Change line 34 from:**
```cmake
find_package(OpenGL REQUIRED OpenGL GLES3)
```

**To:**
```cmake
find_package(OpenGL REQUIRED OpenGL)
```

**Command:**
```bash
sudo sed -i 's/find_package(OpenGL REQUIRED OpenGL GLES3)/find_package(OpenGL REQUIRED OpenGL)/' /usr/local/lib/cmake/SmartSpectra/SmartSpectraConfig.cmake
```

### 2. Patch SmartSpectra Targets

Edit `/usr/local/lib/cmake/SmartSpectra/SmartSpectraTargets.cmake`:

**Replace all instances of `OpenGL::GLES3` with `GLESv2`**

**Command:**
```bash
sudo sed -i 's/OpenGL::GLES3/GLESv2/g' /usr/local/lib/cmake/SmartSpectra/SmartSpectraTargets.cmake
```

### 3. Install Additional Mesa Packages

Beyond the packages listed in the README, you also need:

```bash
sudo apt install -y libgl1-mesa-dev mesa-common-dev libegl1-mesa-dev
```

### 4. CMake Version Adjustment

The README specifies CMake 3.27.0+, but Ubuntu 22.04 ships with CMake 3.22.1. For the hello_vitals example, adjust the CMakeLists.txt:

**Change:**
```cmake
cmake_minimum_required(VERSION 3.27.0)
```

**To:**
```cmake
cmake_minimum_required(VERSION 3.22)
```

## Complete Installation Steps (Including Patches)

```bash
# 1. Install prerequisites
sudo apt update
sudo apt install -y gpg curl
sudo apt install -y build-essential git lsb-release libcurl4-openssl-dev libssl-dev pkg-config libv4l-dev libgles2-mesa-dev libunwind-dev cmake

# 2. Install additional Mesa packages (not in README)
sudo apt install -y libgl1-mesa-dev mesa-common-dev libegl1-mesa-dev

# 3. Add Presage repository
curl -s "https://presage-security.github.io/PPA/KEY.gpg" | gpg --dearmor | sudo tee /etc/apt/trusted.gpg.d/presage-technologies.gpg >/dev/null
sudo curl -s --compressed -o /etc/apt/sources.list.d/presage-technologies.list "https://presage-security.github.io/PPA/presage-technologies.list"

# 4. Update and install SDK (use version 2.0.4 as 2.1.0 dependencies not available)
sudo apt update
sudo apt install -y libsmartspectra-dev=2.0.4

# 5. Apply patches to SmartSpectra CMake files
sudo sed -i 's/find_package(OpenGL REQUIRED OpenGL GLES3)/find_package(OpenGL REQUIRED OpenGL)/' /usr/local/lib/cmake/SmartSpectra/SmartSpectraConfig.cmake
sudo sed -i 's/OpenGL::GLES3/GLESv2/g' /usr/local/lib/cmake/SmartSpectra/SmartSpectraTargets.cmake

# 6. Create hello_vitals.cpp (from README)
# 7. Create CMakeLists.txt with cmake_minimum_required(VERSION 3.22)
# 8. Build
mkdir build && cd build
cmake .. && make
```

## Why These Patches Are Needed

1. **GLES3 vs GLESv2**: Ubuntu 22.04's OpenGL ES implementation provides GLES3 functionality through the GLESv2 library. CMake 3.22's `FindOpenGL` module doesn't have proper support for detecting GLES3 as a separate component.

2. **CMake Version**: Ubuntu 22.04 LTS ships with CMake 3.22.1. While newer CMake versions can be manually installed, the 3.22.1 version is sufficient for building the SDK examples.

3. **Mesa Packages**: Additional mesa development packages are required for full OpenGL/EGL support that weren't explicitly listed in the README prerequisites.

4. **SDK Version**: The latest SDK version (2.1.0) requires `libphysiologyedge-dev >= 2.1.0`, but the Presage PPA only provides up to version 2.0.4 for Ubuntu 22.04. Using SDK version 2.0.4 resolves this dependency mismatch.

## Verification

After applying patches, verify the compilation:

```bash
cd build
./hello_vitals
```

Expected output:
```
Usage: ./hello_vitals YOUR_API_KEY
Or set SMARTSPECTRA_API_KEY environment variable
Get your API key from: https://physiology.presagetech.com
```

## Notes

- These patches modify system-wide SmartSpectra configuration files
- The patches are specific to Ubuntu 22.04 and may not be needed on other distributions
- For production use, contact Presage Technologies for official Ubuntu 22.04 packages
- The pre-built examples (`rest_continuous_example`) in `/usr/local/bin/` work without these patches as they were compiled with the correct library references
