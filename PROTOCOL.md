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

## Mapowanie rejestrów (potwierdzone na żywym urządzeniu)
| Rejestr | Znaczenie | Skala |
|---|---|---|
| 1129 | flaga statusu (5=parowanie?, 1=normalny) | — |
| 1134 / 1135 | Tin / Tout (temperatura wejścia/wyjścia) | ×0.1 °C |
| 1137 | przepływ (tylko podczas poboru wody) | ×0.1 l/min |
| 1138 | aktualna moc grzania (tylko podczas poboru) | ÷1000 kW |
| 1139 / 1141 / 1145 | powiązane z grzaniem (do zbadania) | — |
| 1140 | temperatura zadana (zapis tylko w trybie ręcznym) | ×0.1 °C |
| 1390 | tryb: 0=profil, 1=ręczny | — |
| 1391–1393 | Profile 1–3 (zapis działa) | ×0.1 °C |
| 1394/1395 | limity profili | ×0.1 °C |
| 1008/1009 | min/max nastawy (300..600) | ×0.1 °C |
| 1143/1144 | moce (15000, 10000 W) | — |
| 1520 | energia — miesiąc (32-bit lo; para z 1521) | ÷1000 kWh |
| 1578–1638 | woda dziennie, 31 dni od dziś wstecz | ×0.1 l |
| 1644/1645 | woda — miesiąc (para 32-bit) | ÷100 l |

## Błędy
- `-10`: niedozwolony znak (zły content-type/format)
- `-11`: zły adres startowy
- `-14`: zła liczba rejestrów
