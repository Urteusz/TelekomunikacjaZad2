import threading
import time

from program import receive_file, send_file

t1 = threading.Thread(target=receive_file, args=('COM2','odbiornik_pdf.pdf',True))
t2 = threading.Thread(target=send_file,    args=('COM3','kody.pdf',True))

t1.start()
time.sleep(1)  # daj chwilę na inicjację odbiornika
t2.start()

t1.join()
t2.join()
