# Local bullet
System do wyświetlania lokalnego rankingu konkursów typu Náboj, zvibecodowany na potrzeby szkolnego konkursu
### Wymagania:
- [Python](https://www.python.org/downloads/) `3.10` bądź nowszy. Rekomendowany `3.12` bądź wyżej
- Przeglądarka internetowa
- git oraz gh (do instalacji, opcjonalne)
### Instalacja:
Upewnij się, że `gh` jest zalogowany na konto, które ma dostęp do repo (`gh auth login`). Następnie w katalogu w którym chcesz trzymać bulleta odpal `gh repo clone sgozdal/local-bullet`. Powstanie katalog `local-bullet`. Oczywiście możesz też skopiować plik `local_bullet.py` z githuba do `cokolwiek.py` na swoim komputerze, całość jest używalna jako jeden plik
### Odpalanie
W `local-bullet` odpal plik `local_bullet.py` (najłatwiej: `python3 local_bullet.py`). Spowoduje to otworzenie się adresu `http://127.0.0.1:8000/admin` w nowej karcie przeglądarki. Pod tym adresem będzie chodził cały system. Dopóki nie postawisz w lokalnej sieci, tylko komputer na którym program zostanie odpalony będzie miał dostęp do systemu. Możesz mieć kilka kart włączonych jednoczeście, w różnych oknach różnych przeglądarek. Np.: Jedna karta to punktacja, druga to ranking na pełnym ekranie wyświetlany na jakimś ekranie dla publiki.
Jeśli port 8000 jest zajęty, system sam znajdzie wolny port na którym postawi system.