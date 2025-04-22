import os.path
import threading
import time
from os.path import exists

from program import receive_file, send_file

def information_gui():
    com = input("Podaj port szerergowy: ")
    file = input("Podaj nazwę pliku: ")
    cnc = input("Czy używać CRC? (T/N): ").strip().upper()

    while cnc not in ['T', 'N']:
        print("Niepoprawny wybór, spróbuj ponownie.")
        cnc = input("Czy używać CRC? (T/N): ").strip().upper()
    if cnc == 'T':
        use_crc = True
    else:
        use_crc = False

    return com, file, use_crc

choose_test = input("Wybierz test: 1 - Dwa watki na raz, 2 - Pojedynczy tryb: ")

if choose_test == '1':
    print("Podaj dane odbiornika.")
    com, file, use_crc = information_gui()
    t1 = threading.Thread(target=receive_file, args=(com,file,use_crc))
    print("Podaj dane nadawcy.")
    com, file, use_crc = information_gui()
    t2 = threading.Thread(target=send_file,    args=(com,file,use_crc))

    t1.start()
    time.sleep(1)  # daj chwilę na inicjację odbiornika
    t2.start()

elif choose_test == '2':
    com, file, use_crc = information_gui()

    choose_type = input("Wybierz tryb: 1 - odbiornik, 2 - nadawca: ")

    while choose_type not in ['1', '2']:
        print("Niepoprawny wybór, spróbuj ponownie.")
        choose_type = input("Wybierz tryb: 1 - odbiornik, 2 - nadawca: ")

    if choose_type == '1':
        receive_file(com, file, use_crc)
    elif choose_type == '2':
        send_file(com, file, use_crc)