#$ android.api = 33
#$ android.ndk = 25b
#$ requirements = python3==3.8.10, kivy==2.2.1, requests, certifi, urllib3, android
#$ android.permissions = INTERNET, READ_EXTERNAL_STORAGE, WRITE_EXTERNAL_STORAGE

import os
import sys
import threading
import subprocess
import socket
import time
import shutil
import stat

from kivy.app import App
from kivy.uix.screenmanager import ScreenManager, Screen, FadeTransition
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.floatlayout import FloatLayout
from kivy.uix.label import Label
from kivy.uix.button import Button
from kivy.uix.progressbar import ProgressBar
from kivy.clock import Clock
from kivy.graphics import Color, Rectangle, RoundedRectangle
from kivy.utils import platform
from kivy.core.window import Window
from kivy.metrics import dp, sp

# ─── Platform-specific imports ──────────────────────────────────────────────

if platform == 'android':
    from android.permissions import request_permissions, Permission, check_permission
    from android import mActivity
    from jnius import autoclass, cast, PythonJavaClass, java_method

    # Android Java classes needed for native WebView
    PythonActivity   = autoclass('org.kivy.android.PythonActivity')
    WebView          = autoclass('android.webkit.WebView')
    WebViewClient    = autoclass('android.webkit.WebViewClient')
    WebSettings      = autoclass('android.webkit.WebSettings')
    LinearLayout     = autoclass('android.widget.LinearLayout')
    LayoutParams     = autoclass('android.view.ViewGroup$LayoutParams')
    View             = autoclass('android.view.View')
    Runnable         = autoclass('java.lang.Runnable')
    ActivityInfo     = autoclass('android.content.pm.ActivityInfo')

# ─── Constants ───────────────────────────────────────────────────────────────

SERVER_PORT      = 8080
SERVER_URL       = f'http://localhost:{SERVER_PORT}'
FFMPEG_ARM64_URL = 'https://github.com/nicehash/ffmpeg-android/releases/download/n6.0/ffmpeg-arm64-v8a'
YTDLP_URL        = 'https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp'

APP_GREEN        = (0.0, 1.0, 0.4, 1)
APP_GREEN_HEX    = '#00ff66'
APP_BG           = (0.059, 0.059, 0.071, 1)
APP_CARD         = (0.094, 0.094, 0.110, 1)
APP_TEXT         = (0.9, 0.9, 0.9, 1)
APP_MUTED        = (0.5, 0.5, 0.55, 1)

# ─── Helpers ─────────────────────────────────────────────────────────────────

def get_files_dir():
    """Return the app's internal private storage directory."""
    if platform == 'android':
        return mActivity.getFilesDir().getAbsolutePath()
    # Fallback for desktop testing
    path = os.path.join(os.path.expanduser('~'), '.smart_shorts_dev')
    os.makedirs(path, exist_ok=True)
    return path


def get_cache_dir():
    if platform == 'android':
        return mActivity.getCacheDir().getAbsolutePath()
    path = os.path.join(os.path.expanduser('~'), '.smart_shorts_cache')
    os.makedirs(path, exist_ok=True)
    return path


def is_port_open(port, host='127.0.0.1', timeout=1.0):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def make_executable(path):
    st = os.stat(path)
    os.chmod(path, st.st_mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def update_label_safe(label, text):
    """Thread-safe label update via Clock."""
    Clock.schedule_once(lambda dt: setattr(label, 'text', text), 0)


def rgba(*args):
    return args

# ─── Styled Widgets ──────────────────────────────────────────────────────────

class GreenButton(Button):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.background_normal  = ''
        self.background_color   = (0, 0, 0, 0)
        self.color              = (0, 0, 0, 1)
        self.font_size          = sp(17)
        self.bold               = True
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *args):
        self.canvas.before.clear()
        with self.canvas.before:
            Color(0.0, 1.0, 0.4, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])

    def on_press(self):
        with self.canvas.before:
            Color(0.0, 0.8, 0.32, 1)
            RoundedRectangle(pos=self.pos, size=self.size, radius=[dp(12)])

    def on_release(self):
        self._redraw()


class CardLayout(FloatLayout):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        with self.canvas.before:
            Color(*APP_BG)
            self.bg_rect = Rectangle(pos=self.pos, size=self.size)
        self.bind(pos=self._redraw, size=self._redraw)

    def _redraw(self, *args):
        self.bg_rect.pos  = self.pos
        self.bg_rect.size = self.size

# ─── Screens ─────────────────────────────────────────────────────────────────

class SplashScreen(Screen):
    """
    Initial screen. Shows title + "Start Setup" button.
    No backend interaction until button is pressed.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        root = CardLayout()

        # Background gradient feel via layered rectangles
        with root.canvas.before:
            Color(0.059, 0.059, 0.071, 1)
            self._bg = Rectangle(pos=root.pos, size=root.size)

        root.bind(pos=lambda *a: setattr(self._bg, 'pos', root.pos),
                  size=lambda *a: setattr(self._bg, 'size', root.size))

        center = BoxLayout(
            orientation='vertical',
            spacing=dp(18),
            padding=[dp(40), dp(0)],
            size_hint=(0.88, None),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
        )
        center.bind(minimum_height=center.setter('height'))

        # ── Icon / Title ──
        icon = Label(
            text='🎬',
            font_size=sp(64),
            size_hint=(1, None),
            height=dp(90),
        )

        title = Label(
            text='Smart Shorts',
            font_size=sp(34),
            bold=True,
            color=APP_GREEN,
            size_hint=(1, None),
            height=dp(48),
        )

        subtitle = Label(
            text='AI-Powered Viral Clip Generator\nRuns 100% on your device',
            font_size=sp(14),
            color=APP_MUTED,
            halign='center',
            valign='middle',
            size_hint=(1, None),
            height=dp(52),
        )
        subtitle.bind(size=subtitle.setter('text_size'))

        divider = BoxLayout(size_hint=(1, None), height=dp(1))
        with divider.canvas:
            Color(0.2, 0.2, 0.22, 1)
            Rectangle(pos=divider.pos, size=divider.size)
        divider.bind(pos=lambda *a: None, size=lambda *a: None)

        feature_text = (
            '✓  ffmpeg  •  yt-dlp  •  Groq Whisper\n'
            '✓  Word-level subtitles\n'
            '✓  9:16 TikTok / Reels export'
        )
        features = Label(
            text=feature_text,
            font_size=sp(13),
            color=APP_TEXT,
            halign='left',
            valign='middle',
            size_hint=(1, None),
            height=dp(72),
            padding=[dp(8), 0],
        )
        features.bind(size=features.setter('text_size'))

        self.start_btn = GreenButton(
            text='START SETUP',
            size_hint=(1, None),
            height=dp(58),
        )
        self.start_btn.bind(on_release=self._on_start)

        self.permission_label = Label(
            text='',
            font_size=sp(12),
            color=APP_MUTED,
            size_hint=(1, None),
            height=dp(28),
            halign='center',
        )
        self.permission_label.bind(size=self.permission_label.setter('text_size'))

        for w in [icon, title, subtitle, features, self.start_btn, self.permission_label]:
            center.add_widget(w)

        root.add_widget(center)
        self.add_widget(root)

    def _on_start(self, *args):
        self.start_btn.disabled = True
        update_label_safe(self.permission_label, 'Requesting permissions…')

        if platform == 'android':
            request_permissions(
                [Permission.READ_EXTERNAL_STORAGE,
                 Permission.WRITE_EXTERNAL_STORAGE,
                 Permission.INTERNET],
                self._permission_callback,
            )
        else:
            # Desktop dev: skip permission step
            self._proceed_to_loading()

    def _permission_callback(self, permissions, granted):
        all_granted = all(granted)
        if all_granted:
            update_label_safe(self.permission_label, 'Permissions granted ✓')
            Clock.schedule_once(lambda dt: self._proceed_to_loading(), 0.4)
        else:
            self.start_btn.disabled = False
            update_label_safe(
                self.permission_label,
                '⚠ Storage permission required. Please grant and retry.'
            )

    def _proceed_to_loading(self):
        self.manager.transition = FadeTransition(duration=0.35)
        self.manager.current    = 'loading'
        # Kick off background work from the LoadingScreen
        loading_screen = self.manager.get_screen('loading')
        loading_screen.start_background_work()


class LoadingScreen(Screen):
    """
    Shows live status updates while:
      1. Extracting smart_shorts.py
      2. Downloading / verifying ffmpeg & yt-dlp ARM64 binaries
      3. Starting the local Flask/HTTP server
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._server_proc  = None
        self._server_thread = None

        root = CardLayout()

        center = BoxLayout(
            orientation='vertical',
            spacing=dp(16),
            padding=[dp(36), dp(0)],
            size_hint=(0.9, None),
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
        )
        center.bind(minimum_height=center.setter('height'))

        spinner_label = Label(
            text='⚙',
            font_size=sp(52),
            size_hint=(1, None),
            height=dp(70),
        )

        heading = Label(
            text='Initializing Smart Shorts',
            font_size=sp(20),
            bold=True,
            color=APP_GREEN,
            size_hint=(1, None),
            height=dp(36),
            halign='center',
        )
        heading.bind(size=heading.setter('text_size'))

        self.status_label = Label(
            text='Preparing environment…',
            font_size=sp(13),
            color=APP_TEXT,
            halign='center',
            valign='top',
            size_hint=(1, None),
            height=dp(56),
        )
        self.status_label.bind(size=self.status_label.setter('text_size'))

        self.progress = ProgressBar(
            max=100,
            value=0,
            size_hint=(1, None),
            height=dp(8),
        )

        self.detail_label = Label(
            text='',
            font_size=sp(11),
            color=APP_MUTED,
            halign='center',
            size_hint=(1, None),
            height=dp(40),
        )
        self.detail_label.bind(size=self.detail_label.setter('text_size'))

        for w in [spinner_label, heading, self.status_label, self.progress, self.detail_label]:
            center.add_widget(w)

        root.add_widget(center)
        self.add_widget(root)

    # ── Public API called by SplashScreen ────────────────────────────────

    def start_background_work(self):
        t = threading.Thread(target=self._background_worker, daemon=True)
        t.start()

    # ── Progress helpers ─────────────────────────────────────────────────

    def _set_progress(self, value, status='', detail=''):
        def _update(dt):
            self.progress.value = value
            if status:
                self.status_label.text = status
            if detail is not None:
                self.detail_label.text = detail
        Clock.schedule_once(_update, 0)

    # ── Background worker ────────────────────────────────────────────────

    def _background_worker(self):
        files_dir = get_files_dir()
        bin_dir   = os.path.join(files_dir, 'bin')
        os.makedirs(bin_dir, exist_ok=True)

        # Step 1: Extract smart_shorts.py from APK assets → internal storage
        self._set_progress(10, 'Extracting application files…', '')
        server_script = self._extract_smart_shorts(files_dir)
        if not server_script:
            self._fatal('Failed to extract smart_shorts.py from assets.')
            return

        # Step 2: Verify / download ffmpeg
        self._set_progress(25, 'Verifying ffmpeg binary…', 'Checking ARM64 build…')
        ffmpeg_path = os.path.join(bin_dir, 'ffmpeg')
        if not self._verify_binary(ffmpeg_path, ['-version']):
            self._set_progress(30, 'Downloading ffmpeg for ARM64…',
                               'This may take a minute on first run.')
            ok = self._download_binary(FFMPEG_ARM64_URL, ffmpeg_path)
            if not ok or not self._verify_binary(ffmpeg_path, ['-version']):
                self._fatal('ffmpeg download or verification failed.')
                return
        self._set_progress(55, 'ffmpeg ready ✓', '')

        # Step 3: Verify / download yt-dlp
        self._set_progress(58, 'Verifying yt-dlp…', 'Checking latest release…')
        ytdlp_path = os.path.join(bin_dir, 'yt-dlp')
        if not self._verify_binary(ytdlp_path, ['--version']):
            self._set_progress(62, 'Downloading yt-dlp…', '')
            ok = self._download_binary(YTDLP_URL, ytdlp_path)
            if not ok or not self._verify_binary(ytdlp_path, ['--version']):
                self._fatal('yt-dlp download or verification failed.')
                return
        self._set_progress(78, 'yt-dlp ready ✓', '')

        # Step 4: Inject bin_dir into PATH so smart_shorts.py can find binaries
        os.environ['PATH'] = bin_dir + os.pathsep + os.environ.get('PATH', '')

        # Step 5: Launch the local web server silently
        self._set_progress(82, 'Starting local web server…', 'http://localhost:8080')
        launched = self._launch_server(server_script, files_dir)
        if not launched:
            self._fatal('Could not start local server on port 8080.')
            return

        self._set_progress(100, 'Ready! Opening dashboard…', '')
        time.sleep(0.6)

        # Step 6: Switch to WebView screen on the main thread
        Clock.schedule_once(self._open_webview, 0)

    # ── Asset extraction ─────────────────────────────────────────────────

    def _extract_smart_shorts(self, dest_dir):
        dest_path = os.path.join(dest_dir, 'smart_shorts.py')

        # If already extracted (subsequent launches), reuse it
        if os.path.exists(dest_path):
            return dest_path

        if platform == 'android':
            try:
                # Read from the APK's assets folder (packed by Buildozer)
                AssetManager  = mActivity.getAssets()
                input_stream   = AssetManager.open('smart_shorts.py')
                ByteArrayOutputStream = autoclass('java.io.ByteArrayOutputStream')
                baos = ByteArrayOutputStream()
                buf  = [0] * 4096
                buf_jarray = autoclass('java.lang.reflect.Array').newInstance(
                    autoclass('java.lang.Byte').TYPE, 4096
                )
                read = input_stream.read(buf_jarray)
                while read != -1:
                    baos.write(buf_jarray, 0, read)
                    read = input_stream.read(buf_jarray)
                input_stream.close()
                with open(dest_path, 'wb') as f:
                    f.write(bytes(baos.toByteArray()))
                return dest_path
            except Exception as e:
                # Fallback: try Python-level asset read via android.asset_manager
                try:
                    from android.storage import app_storage_path
                    # Some p4a builds expose assets differently
                    asset_src = os.path.join(
                        os.path.dirname(sys.argv[0]), '..', 'assets', 'smart_shorts.py'
                    )
                    if os.path.exists(asset_src):
                        shutil.copy2(asset_src, dest_path)
                        return dest_path
                except Exception:
                    pass
                return None
        else:
            # Desktop dev: smart_shorts.py must be in the same directory as main.py
            src = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'smart_shorts.py')
            if os.path.exists(src):
                shutil.copy2(src, dest_path)
                return dest_path
            return None

    # ── Binary management ────────────────────────────────────────────────

    def _verify_binary(self, path, args):
        if not os.path.exists(path):
            return False
        try:
            make_executable(path)
            result = subprocess.run(
                [path] + args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=10,
            )
            return result.returncode == 0
        except Exception:
            return False

    def _download_binary(self, url, dest_path):
        try:
            import urllib.request
            tmp = dest_path + '.tmp'
            urllib.request.urlretrieve(url, tmp)
            shutil.move(tmp, dest_path)
            make_executable(dest_path)
            return True
        except Exception as exc:
            update_label_safe(self.detail_label, f'Download error: {exc}')
            return False

    # ── Server launch ────────────────────────────────────────────────────

    def _launch_server(self, script_path, cwd):
        # Prefer running as a Python subprocess so it is truly isolated
        python_bin = sys.executable or 'python3'
        env = os.environ.copy()
        env['PYTHONUNBUFFERED'] = '1'
        env['HOME'] = cwd  # smart_shorts.py uses expanduser('~') for its dirs

        try:
            self._server_proc = subprocess.Popen(
                [python_bin, script_path],
                cwd=cwd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                # Detach from any controlling terminal
                start_new_session=True,
            )
        except Exception as exc:
            # If subprocess fails, try in-process threaded mode
            update_label_safe(self.detail_label, f'Subprocess failed, using thread: {exc}')
            return self._launch_server_inprocess(script_path, cwd)

        # Wait up to 15 s for port to open
        deadline = time.time() + 15
        while time.time() < deadline:
            if is_port_open(SERVER_PORT):
                return True
            if self._server_proc.poll() is not None:
                # Process exited early – try in-process fallback
                return self._launch_server_inprocess(script_path, cwd)
            remaining = deadline - time.time()
            update_label_safe(
                self.detail_label,
                f'Waiting for server… ({int(remaining)}s)'
            )
            time.sleep(0.5)

        return False

    def _launch_server_inprocess(self, script_path, cwd):
        """
        In-process fallback: imports and runs the server in a daemon thread.
        This is used when subprocess.Popen is not available/fails on Android.
        """
        import importlib.util
        import importlib

        def _run():
            original_dir = os.getcwd()
            try:
                os.chdir(cwd)
                os.environ['HOME'] = cwd
                spec   = importlib.util.spec_from_file_location('smart_shorts', script_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                # Call the server start function expected to be in smart_shorts.py
                if hasattr(module, 'start_server'):
                    module.start_server()
                elif hasattr(module, 'run'):
                    module.run()
                # If no explicit entry point, the module-level code starts the server
            except SystemExit:
                pass
            except Exception as exc:
                pass
            finally:
                try:
                    os.chdir(original_dir)
                except Exception:
                    pass

        t = threading.Thread(target=_run, daemon=True)
        t.start()
        self._server_thread = t

        deadline = time.time() + 20
        while time.time() < deadline:
            if is_port_open(SERVER_PORT):
                return True
            remaining = deadline - time.time()
            update_label_safe(
                self.detail_label,
                f'Waiting for in-process server… ({int(remaining)}s)'
            )
            time.sleep(0.5)

        return False

    # ── Error handling ───────────────────────────────────────────────────

    def _fatal(self, message):
        def _show(dt):
            self.status_label.text  = '❌  Setup Failed'
            self.detail_label.text  = message
            self.detail_label.color = (1, 0.3, 0.3, 1)
            retry_btn = GreenButton(
                text='RETRY',
                size_hint=(0.6, None),
                height=dp(50),
                pos_hint={'center_x': 0.5},
            )
            retry_btn.bind(on_release=lambda *a: self._retry())
            self.add_widget(retry_btn)
        Clock.schedule_once(_show, 0)

    def _retry(self):
        self.progress.value    = 0
        self.detail_label.color = APP_MUTED
        self.start_background_work()

    # ── Transition to WebView ────────────────────────────────────────────

    def _open_webview(self, dt):
        webview_screen = self.manager.get_screen('webview')
        webview_screen.load_url(SERVER_URL)
        self.manager.transition = FadeTransition(duration=0.4)
        self.manager.current    = 'webview'


class WebViewScreen(Screen):
    """
    Hosts a full-screen native Android WebView.
    Falls back to a Kivy-based message on non-Android platforms.
    """

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._webview   = None
        self._url       = None
        self._webview_added = False

        root = CardLayout()

        self._placeholder = Label(
            text='Loading dashboard…',
            font_size=sp(16),
            color=APP_GREEN,
            halign='center',
            pos_hint={'center_x': 0.5, 'center_y': 0.5},
        )
        root.add_widget(self._placeholder)
        self.add_widget(root)

    def load_url(self, url):
        self._url = url
        if platform == 'android':
            # Defer WebView creation until screen is active
            Clock.schedule_once(self._create_webview, 0.1)
        else:
            self._placeholder.text = (
                f'[Desktop mode]\nOpen your browser at:\n{url}'
            )

    def on_enter(self):
        if platform == 'android' and self._url and not self._webview_added:
            Clock.schedule_once(self._create_webview, 0.05)

    def _create_webview(self, dt):
        if self._webview_added:
            return

        activity = PythonActivity.mActivity

        def _build_webview():
            wv = WebView(activity)
            settings = wv.getSettings()
            settings.setJavaScriptEnabled(True)
            settings.setDomStorageEnabled(True)
            settings.setLoadWithOverviewMode(True)
            settings.setUseWideViewPort(True)
            settings.setBuiltInZoomControls(False)
            settings.setDisplayZoomControls(False)
            settings.setMediaPlaybackRequiresUserGesture(False)
            settings.setAllowFileAccess(True)
            settings.setAllowContentAccess(True)
            settings.setCacheMode(WebSettings.LOAD_DEFAULT)

            wv.setWebViewClient(WebViewClient())
            wv.setScrollBarStyle(View.SCROLLBARS_OUTSIDE_OVERLAY)
            wv.setScrollbarFadingEnabled(False)

            # Full-screen layout params
            params = LayoutParams(
                LayoutParams.MATCH_PARENT,
                LayoutParams.MATCH_PARENT,
            )
            wv.setLayoutParams(params)

            # Add to the activity's root view
            content_view = activity.getWindow().getDecorView()
            root_view    = cast(
                'android.widget.FrameLayout',
                content_view.findViewById(autoclass('android.R').id.content)
            )
            root_view.addView(wv)

            wv.loadUrl(self._url)
            self._webview = wv

        activity.runOnUiThread(_build_webview)
        self._webview_added = True
        Clock.schedule_once(lambda dt: setattr(self._placeholder, 'text', ''), 0.2)

    def go_back(self):
        if self._webview and self._webview.canGoBack():
            self._webview.goBack()
            return True
        return False

# ─── App Root ─────────────────────────────────────────────────────────────────

class SmartShortsApp(App):
    title    = 'Smart Shorts'
    icon     = 'assets/icon.png'    # Place 512×512 icon.png in your assets/ folder

    def build(self):
        Window.clearcolor = APP_BG

        sm = ScreenManager()
        sm.add_widget(SplashScreen(name='splash'))
        sm.add_widget(LoadingScreen(name='loading'))
        sm.add_widget(WebViewScreen(name='webview'))
        sm.current = 'splash'
        return sm

    def on_start(self):
        if platform == 'android':
            # Keep screen on while processing
            try:
                activity = PythonActivity.mActivity
                activity.getWindow().addFlags(
                    autoclass('android.view.WindowManager$LayoutParams').FLAG_KEEP_SCREEN_ON
                )
                # Force portrait
                activity.setRequestedOrientation(
                    ActivityInfo.SCREEN_ORIENTATION_PORTRAIT
                )
            except Exception:
                pass

    def on_back_press(self):
        """Handle Android back button — navigate WebView history first."""
        sm = self.root
        if sm.current == 'webview':
            webview_screen = sm.get_screen('webview')
            return webview_screen.go_back()
        return False

    def on_stop(self):
        """Clean up on app exit."""
        loading = self.root.get_screen('loading')
        if loading._server_proc:
            try:
                loading._server_proc.terminate()
                loading._server_proc.wait(timeout=3)
            except Exception:
                pass


# ─── Entry point ──────────────────────────────────────────────────────────────

if __name__ == '__main__':
    SmartShortsApp().run()
