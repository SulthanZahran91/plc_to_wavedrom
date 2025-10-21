# Contributing to PLC Log Visualizer

First off, thank you for considering contributing to the PLC Log Visualizer! Your help is greatly appreciated.

## Project Structure

The project is organized into the following directories:

-   `models`: Contains data classes and models that represent the application's data, such as `ParsedLog` and `ParseResult`.
-   `parsers`: Houses the logic for parsing different log file formats. Each parser should implement a common interface.
-   `ui`: Contains all the PyQt6 user interface components, such as `MainWindow`, `WaveformView`, and other widgets.
-   `utils`: A collection of utility functions and classes that are used across the application.

## Coding Style

-   **PEP 8**: All Python code should follow the [PEP 8 style guide](https://www.python.org/dev/peps/pep-0008/).
-   **Type Hinting**: All functions and methods should include type hints for their arguments and return values.
-   **PyQt6**: Follow the standard PyQt6 conventions for UI development. Use signals and slots for communication between components.
-   **Naming Conventions**:
    -   Classes: `PascalCase`
    -   Functions and variables: `snake_case`
    -   Private methods: `_leading_underscore`

## Modularization

To keep the application maintainable, we encourage a modular approach to adding new features. When adding a new UI component, follow these steps:

1.  **Create a new widget**: Create a new `.py` file in the `ui` directory for your widget.
2.  **Encapsulate logic**: The widget should encapsulate its own logic and UI elements.
3.  **Integrate into `MainWindow`**: Add an instance of your widget to the `MainWindow` in `ui/main_window.py`.
4.  **Use signals and slots**: Use signals and slots to communicate between your widget and the `MainWindow`.

## Custom Menu Integration

Here's a step-by-step guide on how to add a custom menu to the `MainWindow` that uses the parsed signal data:

1.  **Create a new menu**: In `ui/main_window.py`, create a new method to handle your custom logic. This method will be connected to your menu item.

    ```python
    def _on_custom_menu_action(self):
        if self._signal_data_list:
            # Your logic here, e.g., print the names of all signals
            for signal in self._signal_data_list:
                print(f"Signal: {signal.name}")
    ```

2.  **Add the menu to `_init_ui`**: In the `_init_ui` method, create a new menu bar and add a "Custom Menu" with a "Show Signals" action.

    ```python
    # In MainWindow._init_ui, after self.setWindowTitle(...)
    menu_bar = self.menuBar()
    custom_menu = menu_bar.addMenu("Custom Menu")
    show_signals_action = custom_menu.addAction("Show Signals")
    show_signals_action.triggered.connect(self._on_custom_menu_action)
    ```

3.  **Accessing parsed data**: The `_on_custom_menu_action` method can access the parsed signal data through `self._signal_data_list`, which is populated after a log file is successfully parsed.
