# 🚀 Odutech Solutions — Custom Third-Party Odoo Addons

[![Odoo Version](https://img.shields.io/badge/Odoo-16.0%20%7C%2017.0%20%7C%2018.0%20%7C%2019.0-714B67.svg)](https://www.odoo.com)
[![Python Version](https://img.shields.io/badge/Python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org)
[![Platform](https://img.shields.io/badge/Platform-Ubuntu%2022.04%20%7C%2024.04%20LTS-orange.svg)](https://ubuntu.com)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)

Welcome to the official custom third-party addons repository for **Odutech Solutions**. This suite of enterprise-grade modules extends Odoo's core capabilities by introducing a high-performance headless REST API framework, strict multi-tenant isolation, and custom cryptographic security enhancements.

---

## 📋 Table of Contents

- [Architectural Overview](#-architectural-overview)
- [Key Features](#-key-features)
- [Getting Started](#%EF%B8%8F-getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Configuration](#configuration)
- [Production Service Management](#-production-service-management-ubuntu-systemd)
- [📡 REST API Reference](#-rest-api-reference)
- [🧪 Automated Testing Protocol](#-automated-testing-protocol)
- [🛡️ Production Security Hardening](#%EF%B8%8F-production-security-hardening)

---

## 🏗️ Architectural Overview

The core engine in this ecosystem (`odutech_odoo_rest_api`) decouples Odoo's backend processing layer, allowing it to act as a secure backend service provider for external applications.

--

## ✨ Key Features

- **Strict Multi-Tenant Isolation:** Resource access control and querying boundaries are strictly locked down using native Odoo `company_id` filters to guarantee complete tenant data privacy.
- **Custom Bcrypt Cryptography:** Overrides Odoo’s default PBKDF2 scheme at the ORM model level (`_set_password` and `_check_credentials`) to automatically salt and hash user passwords using standard `bcrypt`.
- **Token-Based API Access:** Tracking for user registration validation lifecycles and api access points are fully isolated via explicit `res.users.token` relation records.
- **Pre-Creation Verification:** High-performance queries run `search_count()` checks across `res.partner`, `res.users`, and `res.company` tables to proactively block duplicate phone numbers or email registries before transaction insertion.

---

## 🛠️ Getting Started

Follow these steps to deploy and initialize the Odutech module suite within your Odoo environment.

### Prerequisites

Ensure your target system meets the following infrastructure baseline specs:
- **Odoo Core Engine:** v16.0, v17.0, v18.0, or v19.0 (Community or Enterprise)
- **Database Engine:** PostgreSQL 15+
- **Python Dependencies:** `bcrypt` and `psycopg2-binary`

### Installation

1. **Clone the repository:**
   Navigate to your Odoo installation's custom addons path and clone the codebase:
   ```bash
   cd /path/to/your/odoo/custom_addons/
   git clone [https://github.com/odutechsolutions/odutech_odoo_rest_api.git](https://github.com/odutechsolutions/odutech_odoo_rest_api.git)