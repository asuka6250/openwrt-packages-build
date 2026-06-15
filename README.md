# OpenWrt Packages Auto-Build

![OpenWrt 24.10](https://img.shields.io/badge/OpenWrt-24.10-0071e3?logo=openwrt&style=flat-square)
![OpenWrt 25.12](https://img.shields.io/badge/OpenWrt-25.12-ff5a00?logo=openwrt&style=flat-square)
![Build Status](https://img.shields.io/badge/Build-Passing-brightgreen?logo=github-actions&style=flat-square)
![Sync Status](https://img.shields.io/badge/Upstream_Sync-Daily-blueviolet?style=flat-square)

本项目是一个高度自动化的 OpenWrt 第三方软件包（Packages）编译仓库。依托于 GitHub Actions 强大的 CI/CD 能力，本仓库每天定时拉取最新的上游源码，并基于官方 SDK 为主流架构提供预编译的软件包分发服务。

所有编译产物均原生支持 OpenWrt 环境，开箱即用，旨在为软路由爱好者和开发者提供最新、最稳定的插件体验。


## 支持设备 (Supported Architectures)

目前编译矩阵已涵盖以下官方 SDK 版本及硬件架构：

| 硬件架构 (Architecture) | CPU 内核 / 代表设备举例 | OpenWrt 24.10 | OpenWrt 25.12 |
| :--- | :--- | :---: | :---: |
| `x86_64` | Intel / AMD 传统 x86 软路由 | ✅ 支持 | ✅ 支持 |
| `aarch64_cortex-a53` | NanoPi R2S, 斐讯 N1 等 | ✅ 支持 | ✅ 支持 |
| `aarch64_cortex-a72` | 树莓派 4B, NanoPi R4S 等 | ✅ 支持 | ✅ 支持 |
| `aarch64_cortex-a76` | 树莓派 5, RK3588 系列等 | ✅ 支持 | ✅ 支持 |
| `aarch64_generic` | 通用 ARM64 架构设备 | ✅ 支持 | ✅ 支持 |

> **提示**：您可以通过在路由器终端执行 `cat /etc/os-release` 或 `opkg print-architecture` 来确认您设备的具体架构类型。

## 🔗 上游源码 (Upstream Source)

本仓库的所有软件包源码由以下仓库提供。

* **Upstream Repository**: [asuka6250/openwrt-packages](https://github.com/asuka6250/openwrt-packages)


---

*This project is built automatically by GitHub Actions. Feel free to open issues or pull requests if you encounter any build problems.*
