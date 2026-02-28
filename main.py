from qt_ui.app import MainWindow, build_app


if __name__ == "__main__":
    app = build_app()
    window = MainWindow()
    window.show()
    app.exec()
