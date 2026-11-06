# KOSPEL PPE4 — protokół HTTP (potwierdzony na żywo, piec 192.168.1.94)

## Ogólne

- REST JSON, User-Agent aplikacji: `KOSPEL RESTClient/1.0`
- Odpowiedź: `{"ver":"1.0","status":"OK","status_value":"0","res":{"<rejestr>":<wartość>,...}}`
- Rejestry = MODBUS-like adresy 16-bit; statystyki są 32-bit (para rejestrów lo/hi: 1520/1521 itd.)
- Zmapowany obszar to 1000–1895. Zakres obejmujący nieistniejący rejestr (np. 1440–1447, 1568–1570) zwraca zepsuty JSON: `"res":}}`
- Serwer HTTP gubi połączenia równoległe — zapytania trzeba wysyłać pojedynczo
- Aplikacja KOSPEL opisuje miesiące od bieżącego wstecz („styczeń” = bieżący miesiąc); rejestry są ułożone kalendarzowo
- Urządzenie ma też stronę konfiguracji WiFi pod `http://<ip>/` (AP `ppe4_0000xxxx`, hasło domyślne `12345678`, config AP: 192.168.8.1)

## Odczyt

`GET http://<ip>/api/<start>/<count>` → res z rejestrami start..start+count-1

## Zapis

`POST /api/write`, **Content-Type: application/json**, body = `{"<rejestr>":<wartość>}`
(form-urlencoded NIE działa — błąd -10). Zapis nieistniejącego rejestru zwraca OK ale nic nie robi.
JSON musi być zwarty: `{"1390": 1}` ze spacją po dwukropku też kończy się błędem -10.

## Mapowanie rejestrów (potwierdzone na żywym urządzeniu)

| Rejestr | Znaczenie | Skala |
| --- | --- | --- |
| 1129 | flaga statusu (5=parowanie?, 1=normalny) | — |
| 1134 / 1135 | Tin / Tout (temperatura wejścia/wyjścia) | ×0.1 °C |
| 1137 | przepływ (tylko podczas poboru wody) | ×0.1 l/min |
| 1138 | aktualna moc grzania (tylko podczas poboru) | ÷1000 kW |
| 1139 / 1141 / 1145 | powiązane z grzaniem (do zbadania) | — |
| 1140 | temperatura zadana aktualnie obowiązująca (podąża za 1390) | ×0.1 °C |
| 1390 | aktywny profil: 0=ręczny, 1–3=profile z aplikacji (nazwy nadaje użytkownik; zapis działa) | — |
| 1391 | nastawa ręczna (zapis działa) | ×0.1 °C |
| 1392–1394 | temperatury profili 1–3 (zapis działa) | ×0.1 °C |
| 1395 | nieznane (700) | ×0.1 °C |
| 1008/1009 | min/max nastawy (300..600) | ×0.1 °C |
| 1143/1144 | moce (15000, 10000 W) | — |
| 1448 / 1576 | dzień tygodnia (1 = poniedziałek), przed tablicą dni energii / wody | — |
| 1450–1511 | energia dziennie, 31 par, od dziś wstecz | Wh |
| 1512 | energia — ostatnie 7 dni (suma krocząca) | Wh |
| 1514 / 1516 / 1518 | energia — bieżący rok / poprzedni rok / licznik całkowity | Wh |
| 1520–1543 | energia miesięcznie, bieżący rok, 12 par od stycznia | Wh |
| 1544–1567 | energia miesięcznie, poprzedni rok, 12 par od stycznia | Wh |
| 1578–1639 | woda dziennie, 31 par, od dziś wstecz | ×0.1 l |
| 1640 | woda — ostatnie 7 dni (suma krocząca) | ×0.1 l |
| 1642 / 1644 / 1646 | woda — bieżący rok / poprzedni rok / licznik całkowity | ×0.1 l |
| 1648–1671 | woda miesięcznie, bieżący rok, 12 par od stycznia | ×0.1 l |
| 1672–1695 | woda miesięcznie, poprzedni rok, 12 par od stycznia | ×0.1 l |

## Błędy

- `-10`: niedozwolony znak (zły content-type/format)
- `-11`: zły adres startowy
- `-14`: zła liczba rejestrów
