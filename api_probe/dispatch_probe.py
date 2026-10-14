try:
 import win32com.client
 a=win32com.client.DispatchEx('MultisimInterface.MultisimApp')
 print('APP',a.Path,a.IsConnected)
except Exception as e: print(repr(e))
