## Installation Instructions for gptchangelog

### Prerequisites

Make sure you have Python installed on your system. You can download Python from [python.org](https://www.python.org/).

### Steps to Install

1. **Clone the Repository:**

   First, you need to clone the repository. Open your terminal and run:

   ```sh
   git clone https://github.com/xjodoin/gptchangelog.git
   cd src
   ```

2. **Create a Virtual Environment (Optional but Recommended):**

   It's a good practice to create a virtual environment to avoid dependency conflicts. Run the following commands:

   ```sh
   python -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install the Required Dependencies:**

   With your virtual environment activated, install the project dependencies using `setup.py`:

   ```sh
   pip install .
   ```

   If you are developing the project and need to install it in editable mode, use:

   ```sh
   pip install -e .
   ```

### Verify the Installation

You can verify the installation by running the `gptchangelog` command:

```sh
src --help
```

### Additional Information

- **Running Tests:** (if applicable)
  
  If your project includes tests, you can run them with:

  ```sh
  pytest
  ```

- **Uninstalling:**
  
  To uninstall the project, simply run:

  ```sh
  pip uninstall src
  ```

### Troubleshooting

- **Common Issues:** Provide solutions for common issues here.
- **Support:** Include information on how to get support if they run into problems (e.g., creating an issue on GitHub).
