using System;
using System.Diagnostics;
using System.IO;
using System.Net;
using System.Threading;
using System.Windows.Forms;

namespace AnyPS5Launcher
{
    static class Program
    {
        [STAThread]
        static void Main(string[] args)
        {
            string appDir = AppDomain.CurrentDomain.BaseDirectory;
            string pythonPath = FindPython();
            if (string.IsNullOrEmpty(pythonPath))
            {
                MessageBox.Show(
                    "Python 3.10+ is required to run AnyPS5 Launcher.\n\nPlease install Python from https://python.org and check 'Add Python to PATH'.",
                    "AnyPS5 Launcher",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error
                );
                return;
            }

            // 1. Start Python backend server in background with hidden window
            Process pyProc = null;
            try
            {
                ProcessStartInfo pyPsi = new ProcessStartInfo
                {
                    FileName = pythonPath,
                    Arguments = "launcher.py --daemon",
                    WorkingDirectory = appDir,
                    UseShellExecute = false,
                    CreateNoWindow = true,
                    WindowStyle = ProcessWindowStyle.Hidden
                };
                pyProc = Process.Start(pyPsi);
            }
            catch (Exception ex)
            {
                MessageBox.Show("Failed to start launcher backend: " + ex.Message, "AnyPS5 Launcher Error", MessageBoxButtons.OK, MessageBoxIcon.Error);
                return;
            }

            // 2. Poll http://127.0.0.1:8085/api/status until ready
            bool ready = false;
            for (int i = 0; i < 30; i++)
            {
                try
                {
                    HttpWebRequest req = (HttpWebRequest)WebRequest.Create("http://127.0.0.1:8085/api/status");
                    req.Timeout = 600;
                    using (HttpWebResponse resp = (HttpWebResponse)req.GetResponse())
                    {
                        if (resp.StatusCode == HttpStatusCode.OK)
                        {
                            ready = true;
                            break;
                        }
                    }
                }
                catch
                {
                    Thread.Sleep(200);
                }
            }

            // 3. Launch native standalone app window (No URL bar, no tabs)
            string browser = FindBrowser();
            if (!string.IsNullOrEmpty(browser))
            {
                string dataDir = Path.Combine(appDir, ".app_data");
                ProcessStartInfo appPsi = new ProcessStartInfo
                {
                    FileName = browser,
                    Arguments = string.Format("--app=http://127.0.0.1:8085 --window-size=1380,880 --user-data-dir=\"{0}\"", dataDir),
                    UseShellExecute = false
                };

                try
                {
                    using (Process appProc = Process.Start(appPsi))
                    {
                        if (appProc != null)
                        {
                            appProc.WaitForExit();
                        }
                    }
                }
                catch {}
            }
            else
            {
                Process.Start("http://127.0.0.1:8085");
            }

            // 4. Clean up background python server upon closing the app
            try
            {
                if (pyProc != null && !pyProc.HasExited)
                {
                    pyProc.Kill();
                }
            }
            catch {}
        }

        static string FindPython()
        {
            string[] names = { "pythonw.exe", "python.exe" };
            foreach (string name in names)
            {
                try
                {
                    ProcessStartInfo psi = new ProcessStartInfo
                    {
                        FileName = "where",
                        Arguments = name,
                        UseShellExecute = false,
                        RedirectStandardOutput = true,
                        CreateNoWindow = true
                    };
                    using (Process p = Process.Start(psi))
                    {
                        string outStr = p.StandardOutput.ReadToEnd();
                        p.WaitForExit();
                        string[] lines = outStr.Split(new char[] { '\r', '\n' }, StringSplitOptions.RemoveEmptyEntries);
                        if (lines.Length > 0 && File.Exists(lines[0]))
                            return lines[0];
                    }
                }
                catch {}
            }
            return null;
        }

        static string FindBrowser()
        {
            string[] candidates = {
                @"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                @"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
                @"C:\Program Files\Google\Chrome\Application\chrome.exe",
                @"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"
            };
            foreach (string path in candidates)
            {
                if (File.Exists(path)) return path;
            }
            return null;
        }
    }
}
