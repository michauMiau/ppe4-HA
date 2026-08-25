# KOSPEL PPE4 — protokół HTTP (potwierdzony na żywo, piec 192.168.1.94)

## Ogólne
- REST JSON, User-Agent aplikacji: `KOSPEL RESTClient/1.0`
- Odpowiedź: `{"ver":"1.0","status":"OK","status_value":"0","res":{"<rejestr>":<wartość>,...}}`
- Rejestry = MODBUS-like adresy 16-bit; statystyki są 32-bit (para rejestrów lo/hi: 1520/1521 itd.)
- Urządzenie ma też stronę konfiguracji WiFi pod `http://<ip>/` (AP `ppe4_0000xxxx`, hasło domyślne `12345678`, config AP: 192.168.8.1)

## Odczyt
`GET http://<ip>/api/<start>/<count>` → res z rejestrami start..start+count-1

## Zapis
`POST /api/write`, **Content-Type: application/json**, body = `{"<rejestr>":<wartość>}`
(form-urlencoded NIE działa — błąd -10). Zapis nieistniejącego rejestru zwraca OK ale nic nie robi.

## Mapowanie rejestrów (odczyt 1390/6)
| Rejestr | Znaczenie | Wartości obserwowane |
|---|---|---|
| 1390 | tryb pracy / profil | 0 |
| 1391 | temperatura zadana (nastawa) ×10? | 360→350 po zapisie {"1391":350} — **zapis potwierdzony działaniem** |
| 1392 | min nastawy | 350 |
| 1393 | ? | 450 |
| 1394 | ? | 550 |
| 1395 | max nastawy | 700 |

Uwaga: 350 przy pokazanym w appce TEMP... wartości w °C×10 prawdopodobnie (35°C na ekranie tutorialu). Do potwierdzenia: jednostka i czy 1391 to °C×10.
- 1128–1152: status/ikony/czas (1143=15000, 1144=10000 — może moce W)
- 1000–1043: limity/konfiguracja read-only-ish (min/max profili: 300..600/750)
- 1520+: statystyki 32-bit (kWh/m³, okresy rok/tydzień)

## Błędy
- `-10`: niedozwolony znak (zły content-type/format)
- `-11`: zły adres startowy
- `-14`: zła liczba rejestrów
