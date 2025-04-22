import serial
import time

# Znaki sterujące XModem
SOH = 0x01  # Start of Header
EOT = 0x04  # End of Transmission
ACK = 0x06  # Acknowledge
NAK = 0x15  # Not Acknowledge
CAN = 0x18  # Cancel
C = 0x43    # 'C' znak sygnalizujący chęć odbioru z CRC

BLOCK_SIZE = 128  # Rozmiar bloku danych w bajtach

# === Funkcje pomocnicze ===
def calculate_checksum(block):
    """Wylicza sumę kontrolną (1 bajt)."""
    return sum(block) % 256

def calculate_crc(block):
    """Wylicza CRC16-CCITT (2 bajty) bez użycia biblioteki."""
    crc = 0x0000
    polynomial = 0x1021
    for byte in block:
        crc ^= (byte << 8)
        for _ in range(8):
            if (crc & 0x8000):
                crc = ((crc << 1) & 0xFFFF) ^ polynomial
            else:
                crc = (crc << 1) & 0xFFFF
    return crc

# === Odbiornik ===
def receive_file(port, filename, use_crc=True):
    """Odbiera plik przez XModem (checksum lub CRC)."""
    print(f"[Odbiornik] Start na porcie {port}, plik wyjściowy: {filename}, tryb: {'CRC' if use_crc else 'checksum'}")
    ser = serial.Serial(port, baudrate=9600, timeout=1)
    time.sleep(2)

    init_char = C if use_crc else NAK

    # Cykliczne wysyłanie znaku inicjalizacji aż do SOH lub EOT
    next_init_time = time.time()
    init_timeout = time.time() + 60  # maksymalnie 60 sekund czekania

    print(f"[Odbiornik] Oczekiwanie na rozpoczęcie transmisji...")

    while True:
        now = time.time()
        if now >= next_init_time:
            ser.write(bytes([init_char]))
            print(f"[Odbiornik] Wysłano inicjalizację: {hex(init_char)}")
            next_init_time = now + 3  # wysyłaj co 3 sekundy

        header = ser.read(1)
        if header:
            code = header[0]
            if code == SOH or code == EOT:
                break  # przejdź do odbioru

        if time.time() > init_timeout:
            print("[Odbiornik] Timeout oczekiwania na nadawcę")
            ser.close()
            return


    # init_char = C if use_crc else NAK
    #
    #
    # ser.write(bytes([init_char]))
    # print(f"[Odbiornik] Ponowiono inicjalizację: {hex(init_char)}")
    # next_init_time = time.time()
    # while True:
    #     now = time.time()
    #     # co sekundę ponawiaj inicjalizację
    #     if now >= next_init_time:
    #         ser.write(bytes([init_char]))
    #         next_init_time = now + 1
    #         print(f"[Odbiornik] Ponowiono inicjalizację: {hex(init_char)}")
    #     header = ser.read(1)
    #     if not header:
    #         break

    expected_block = 1
    with open(filename, 'wb') as f:
        while True:
            print("[Odbiornik] Czekam na nagłówek lub EOT...")
            header = ser.read(1)
            if not header:
                print("[Odbiornik] Timeout - brak nagłówka")
                continue

            code = header[0]
            if code == SOH:
                print(f"[Odbiornik] Odebrano SOH, oczekiwany blok: {expected_block}")
                block_num = ser.read(1)[0]
                block_num_comp = ser.read(1)[0]
                print(f"[Odbiornik] Numer bloku: {block_num}, komplement: {block_num_comp}")

                if (block_num + block_num_comp) & 0xFF != 0xFF:
                    print("[Odbiornik] Błąd numeru bloku, wysyłam NAK")
                    ser.write(bytes([NAK]))
                    continue

                data = ser.read(BLOCK_SIZE)
                if len(data) < BLOCK_SIZE:
                    print("[Odbiornik] Niepełny blok danych, wysyłam NAK")
                    ser.write(bytes([NAK]))
                    continue

                if use_crc:
                    received_crc = int.from_bytes(ser.read(2), 'big')
                    calc_crc = calculate_crc(data)
                    print(f"[Odbiornik] Otrzymane CRC: {received_crc}, obliczone CRC: {calc_crc}")
                    if received_crc == calc_crc:
                        f.write(data)
                        ser.write(bytes([ACK]))
                        print(f"[Odbiornik] Blok {block_num} OK, wysłano ACK")
                        expected_block += 1
                    else:
                        print("[Odbiornik] CRC niezgodne, wysłano NAK")
                        ser.write(bytes([NAK]))
                else:
                    received_sum = ser.read(1)[0]
                    calc_sum = calculate_checksum(data)
                    print(f"[Odbiornik] Otrzymane checksum: {received_sum}, obliczone checksum: {calc_sum}")
                    if received_sum == calc_sum:
                        f.write(data)
                        ser.write(bytes([ACK]))
                        print(f"[Odbiornik] Blok {block_num} OK, wysłano ACK")
                        expected_block += 1
                    else:
                        print("[Odbiornik] Checksum niezgodne, wysłano NAK")
                        ser.write(bytes([NAK]))

            elif code == EOT:
                print("[Odbiornik] Odebrano EOT, kończę odbiór")
                ser.write(bytes([ACK]))
                print(f"[Odbiornik] Plik zapisany jako {filename}")
                break
            else:
                print(f"[Odbiornik] Otrzymano nieznany znak: {hex(code)}")

    ser.close()

# === Nadawca ===
def send_file(port, filename, use_crc=True):
    """Wysyła plik przez XModem (checksum lub CRC)."""
    print(f"[Nadawca] Start na porcie {port}, plik do wysłania: {filename}, tryb: {'CRC' if use_crc else 'checksum'}")
    ser = serial.Serial(port, baudrate=9600, timeout=1)
    time.sleep(2)

    expected_init = C if use_crc else NAK
    print("[Nadawca] Oczekiwanie na inicjalizację od odbiornika...")
    # ZMIANA: czekaj w pętli na poprawny znak inicjalizacji
    while True:
        init = ser.read(1)
        if init and init[0] == expected_init:
            print(f"[Nadawca] Otrzymano inicjalizację: {hex(init[0])}")
            break
        # w przeciwnym razie powtarzaj odczyt

    block_number = 1
    with open(filename, 'rb') as f:
        while True:
            data = f.read(BLOCK_SIZE)
            if not data:
                print("[Nadawca] Brak danych, przechodzę do EOT")
                break
            data = data.ljust(BLOCK_SIZE, b'\x1A')
            print(f"[Nadawca] Przygotowuję blok {block_number}")

            # Nagłówek i dane
            packet = bytes([SOH, block_number, 255 - block_number]) + data
            if use_crc:
                crc = calculate_crc(data)
                packet += crc.to_bytes(2, 'big')
            else:
                checksum = calculate_checksum(data)
                packet += bytes([checksum])

            # Wysyłka i oczekiwanie na ACK/NAK
            while True:
                print(f"[Nadawca] Wysyłam blok {block_number}")
                ser.write(packet)
                resp = ser.read(1)
                if not resp:
                    print("[Nadawca] Timeout - brak odpowiedzi")
                    continue
                if resp[0] == ACK:
                    print(f"[Nadawca] Blok {block_number} potwierdzony ACK")
                    break
                elif resp[0] == NAK:
                    print(f"[Nadawca] Blok {block_number} odrzucony NAK, ponawiam")
                    continue
                else:
                    print(f"[Nadawca] Otrzymano nieznany znak: {hex(resp[0])}")

            block_number = (block_number + 1) % 256

    # Wysyłka EOT
    while True:
        print("[Nadawca] Wysyłam EOT")
        ser.write(bytes([EOT]))
        ack = ser.read(1)
        if ack and ack[0] == ACK:
            print("[Nadawca] Otrzymano ACK na EOT, zakończono transmisję")
            break

    ser.close()
