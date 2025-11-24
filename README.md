# GuitarTrainer

- Make sure to use Python 3.12.
- If using `uv`, must first `pip install aubio` to the system and manually copy the `aubio` and `aubio-0.4.9.dist-info` folders to your `.venv/Lib/site-packages/` folder. System python packages for Python 3.13 are stored in `C:\Users\<your_username>\AppData\Local\Programs\Python\Python313\Lib\site-packages`.
- Additionally, you must install [Visual Studio Community 2022](https://visualstudio.microsoft.com/vs/community/), ensuring you select **Python development** from the main selection menu and include the following from the right-side menu:
    - `Python native development tools`
    - `Python web support`
- Using the same installer, you may also need to install `Desktop development with C++` from **Visual Studio Build Tools 2022**
- If you continue to encounter build wheel errors, run `pip install --upgrade wheel` and `pip install setuptools`.