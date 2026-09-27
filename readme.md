![CI](https://github.com/rabi-nagy-gergo/SISAL_WebSubmit/actions/workflows/ci.yml/badge.svg)
[![codecov](https://codecov.io/github/rabi-nagy-gergo/SISAL_WebSubmit/graph/badge.svg?token=R8CYNEHYC2)](https://codecov.io/github/rabi-nagy-gergo/SISAL_WebSubmit)

# SISAL Web Submit

## Authors & Contributions

**Web Application & System Architecture**
* **Gergő Rabi-Nagy** – Development of the interactive web application and browser-based validation procedure.

**Core Validation Pipeline (Python & R Scripts)**
* **K. Atsawawaranunt, L. Comas-Bru, E. Pestalozzi, I. Hatvani, L. Endres** – Authors of the original local validation workflow, including the `wb_check_v15.py` structural/scientific validation script and the R-based plotting tools.
* **J. Fohlmeister** – Developer of the original U-Th check logic in Julia (subsequently ported to the Python pipeline).

## About the SISAL Project

SISAL (Speleothem Isotope Synthesis and AnaLysis) is a working group of the Past Global Changes (PAGES) project with the goal to provide a comprehensive compilation of speleothem records for climate reconstruction and model evaluation. Since 2018, four versions of the speleothem-derived stable isotope (&delta;<sup>18</sup>O and &delta;<sup>13</sup>C) database have been published. With each new version released, the available set of records increased; lately, the database was expanded to include speleothem trace element records as well.

Community-curated databases depend on rigorous and reproducible quality control (QC) to remain trustworthy resources for paleoclimate research. As part of the SpeleoFAIR project and the ongoing SISAL–Neotoma integration, SISAL is maintained through a continuously updated submission workbook and an accompanying QC procedure.

### SISAL Database Versions

| Version | Year | Records | Sites | Reference |
| :--- | :--- | :--- | :--- | :--- |
| **v1.0** | 2018 | 381 speleothem records from 174 cave sites | 174 | Atsawawaranunt et al., 2018, ESSD, 10, 1687–1713, [https://doi.org/10.5194/essd-10-1687-2018](https://doi.org/10.5194/essd-10-1687-2018) |
| **v1b** | 2019 | 455 speleothem records from 211 sites | 211 | Atsawawaranunt et al., 2019 (dataset); figures as reported in Comas-Bru et al., 2020, ESSD |
| **v2.0** | 2020 | 691 speleothem records from 294 cave sites, comprising 673 &delta;<sup>18</sup>O / 430 &delta;<sup>13</sup>C records | 294 | Comas-Bru et al., 2020, ESSD, 12, 2579–2606, [https://doi.org/10.5194/essd-12-2579-2020](https://doi.org/10.5194/essd-12-2579-2020) |
| **v3.0** | 2024 | 892 &delta;<sup>18</sup>O / 620 &delta;<sup>13</sup>C records, plus 95 Mg/Ca, 85 Sr/Ca, 52 Ba/Ca, 25 U/Ca, 29 P/Ca, and 14 Sr-isotope records | 365 | Kaushal et al., 2024, ESSD, 16, 1933–1963, [https://doi.org/10.5194/essd-16-1933-2024](https://doi.org/10.5194/essd-16-1933-2024) |

## Introduction
The SISAL Web Submit project transforms the previously decentralized, local validation pipeline into a unified, web-based application. This centralized interface is specifically designed to streamline the uploading, auditing, and scientific validation of speleothem data, completely eliminating the need for contributors to manage local software environments and manual script executions.

This application automates the validation process by providing a user-friendly interface built with Vanilla HTML, Bootstrap, and Vanilla JavaScript, connected to a stateless, file-system-based FastAPI backend. It allows contributors to run complex quality control (AutoQC) and plotting scripts seamlessly from their browsers.

## Submission Workflow
The data submission process is divided into the following sequential stages:

* **Stage 1: File Upload:** The contributor fills out the provided Excel workbook template with their speleothem sample data and uploads it through the web interface.
* **Stage 2: Validation (AutoQC):** The FastAPI backend executes a Python QC script (`wb_check_v15.py`) to validate the workbook's content and structure. This script generates a QC log, a regional site map, and a QC-passed copy of the workbook if no structural or logical errors are found. To optimize this process for the web environment, the script's error messages were restructured into three distinct severity categories (Warning, Error, Fatal). A detailed breakdown of these classifications can be found in [message_categories.md](message_categories.md).
* **Stage 3: Age-Model & Proxy Plotting:** Once the initial validation is successful, an R plotting script (`run_plots.R`) is executed. This script generates a PDF for each entity containing age models, potential hiatuses, and proxy time-series plots. These plots are saved to an output folder and embedded directly into the webpage for visual inspection.
* **Stage 4: Download and Finalization:** As a final step, the contributor can download a `.zip` archive containing the validated Excel file and the PDF plots. The validated data and documentation are then manually forwarded to a SISAL Data Steward to complete the database submission.

## Technical Information (Stack)
* **Backend:** Python, FastAPI
* **Frontend:** Vanilla HTML, Vanilla JavaScript, Bootstrap 5
* **Data Validation (Python):** Requires `pandas`, `numpy`, `openpyxl`, `xlrd`, `matplotlib`, `cartopy`, and `shapely`.
* **Plotting (R):** Requires `openxlsx` and `ggplot2`.
* **Architecture:** Stateless API relying on session UUIDs and temporary file system storage with automated background garbage collection.

## Dockerization
The project operates in a 100% Dockerized multi-stage environment (DEBUG and RELEASE). Environmental dependencies are managed via `.env` files. The development version supports live hot-reloading via volume mounting, while the production version is fully self-contained and optimized for performance.

## Development Guide

### Prerequisites
Before you can run or develop the application, you need to have the following tools installed on your system:

* **Docker:** The application is fully containerized. You must install Docker to build and run the images.
  * For **Windows and macOS**, install [Docker Desktop](https://www.docker.com/products/docker-desktop/).
  * For **Linux** environments, install the [Docker Engine](https://docs.docker.com/engine/install/) along with the [Docker Compose](https://docs.docker.com/compose/install/) plugin.
* **Make (Optional but recommended):** The project uses a `Makefile` to simplify Docker commands. This is usually available by default on Linux and macOS. On Windows, you can either run the underlying `docker compose` commands directly, use WSL2, or install a native Make tool.

### Starting the Application
A `Makefile` is provided to simplify Docker commands. Use the following commands in your terminal:

* **Development mode (DEBUG):** Builds and runs the container with hot-reloading enabled.
  ```bash
  make debug
  ```
  The API and the web interface will be available at `http://localhost:8000` (or as specified in your `.env.debug` file).

* **Production mode (RELEASE):** Builds and runs the optimized, self-contained production container in RELEASE mode (running in the background).
  ```bash
  make release
  ```

* **Stopping the Application:** Safely stops the running container and removes the associated Docker networks.
  ```bash
  make down
  ```

### Note on State Management:
Because the backend is strictly stateless, all uploaded and generated files are isolated in unique UUID folders within a sessions/ directory. A background garbage collection task automatically deletes inactive sessions to prevent the Docker container from running out of storage.
