# SISAL Web Submit

## Introduction
The SISAL Web Submit project transforms an existing local data submission workflow into an interactive web application designed for uploading, auditing, and validating speleothem data. The SISAL speleothem database is one of the largest databases of its kind in the world. Historically, data submission has been manual, requiring significant time and effort. 

This application automates the validation process by providing a user-friendly interface built with Vanilla HTML, Bootstrap, and Vanilla JavaScript, connected to a stateless, file-system-based FastAPI backend. It allows contributors to run complex quality control (AutoQC) and plotting scripts seamlessly from their browsers.

## Submission Workflow
The data submission process is divided into the following sequential stages:

* **Stage 1: File Upload:** The contributor fills out the provided Excel workbook template with their speleothem sample data and uploads it through the web interface.
* **Stage 2: Validation (AutoQC):** The FastAPI backend executes a Python QC script (`wb_check_v15.py`) to validate the workbook's content and structure. This script generates a QC log, a regional site map, and a QC-passed copy of the workbook if no structural or logical errors are found. The web interface parses the standard output to provide immediate feedback on any warnings or informative messages.
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
