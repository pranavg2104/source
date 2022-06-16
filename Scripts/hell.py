import time
import os
import sys


print("Hello")
#vttApp = Dispatch("Vector.VTT.ComServer.ComApplicationImpl")
print("Bye")
print(os.getenv("JAVA_HOME"))
path = "E:\\Pranav\\npp.8.4.1.Installer.x64.exe"
os.environ["JAVA_HOME"] = path
print(os.getenv("JAVA_HOME"))

