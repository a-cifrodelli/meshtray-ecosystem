import pytest
from connection import ConnectionThread

def test_epoch_to_datetime_str():
    # Instanziamo ConnectionThread per accedere alle sue funzioni helper
    thread = ConnectionThread()
    epoch = 1693000000  # 2023-08-25T21:46:40 UTC
    res = thread.epoch_to_datetime_str(epoch)
    
    # 21:46:40 UTC corrisponde alle 23:46:40 in ora locale (Europe/Rome - ora legale +2h)
    assert "2023-08-25 23:46:40" in res

def test_iso_to_local_str():
    thread = ConnectionThread()
    iso_str = "2023-08-25T21:46:40Z"
    res = thread.iso_to_local_str(iso_str)
    
    # Verifica la conversione in ora locale italiana (+2h)
    assert "2023-08-25 23:46:40" in res
