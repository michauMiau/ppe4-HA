# KOSPEL PPE4 — kody błędów (z dekompilacji libPPE4.so)

Kompletna lista komunikatów błędów urządzenia wyciągnięta z zasobów aplikacji
(wielojęzyczne, tu wersja EN + PL gdzie dostępna). Aplikacja mapuje je z rejestrów
statusu (blok 1128–1152 / lista `FillErrorList`/`FillWarningList` w TuData).

## Błędy (Errors)
| # (kolejność w aplikacji) | EN | PL |
|---|---|---|
| 1 | Voltage on probe without heating | Napięcie na czujniku bez grzania |
| 2 | Temperature in sensor damage | Uszkodzenie czujnika temperatury wej. |
| 3 | Temperature out sensor damage | Uszkodzenie czujnika temperatury wyj. |
| 4 | Temperature sensor error, negative power | Błąd czujnika temp., moc ujemna |
| 5 | Turbine operation error / Problem with turbine | Problem z turbiną (przepływomierzem) |
| 6 | Air probe error | Błąd czujnika powietrza |
| 7 | Output temperature above permissible | Temp. na wyjściu powyżej dopuszczalnej |
| 8 | Multiple detection of output temperature above permissible | Wielokrotne wykrycie temp. wyj. ponad dopuszczalną |
| 9 | Exceeding maximum flow value | Przekroczenie maksymalnego przepływu |
| 10 | Network frequency measurement error | Błąd pomiaru częstotliwości sieci |
| 11 | Difference in inlet-outlet sensor readings | Różnica w odczycie czujników wej/wyj |
| 12 | Unknown configuration | Nieznana konfiguracja |
| 13 | Communication problem with internal clock | Problem kom. z zegarem wewnętrznym |
| 14 | Communication problem with I2C bus | Problem kom. z magistralą I2C |
| 15 | Problem with EEPROM API | Problem z zapisem EEPROM |

## Wartości obserwowane
- Rejestr **1129**: `1` = normalna praca, `5` = grzanie aktywne / tryb parowania WiFi
- Rejestry **1130–1133**: flagi błędów (0 = OK); integracja HA pokazuje je jako binary sensor `Usterka` + atrybuty `flag_1130..flag_1133`
- **1136 = 280** — stałe, może kod konfiguracji/mocy urządzenia

## Mapowanie błędów na rejestry (do potwierdzenia)
Aplikacja wypełnia listy błędów/ostrzeżeń z bloku statusu. Prawdopodobne przypisanie
(kolejność tekstów w zasobach odpowiada kolejności bitów/rejestrów):
- 1130 → błędy krytyczne 1–8 (czujniki, turbina, przegrzanie)
- 1131 → błędy 9–12 (przepływ, sieć, konfiguracja)
- 1132/1133 → ostrzeżenia / błędy komunikacji (zegar, I2C, EEPROM)

Weryfikacja: wymusić usterkę (np. odłączyć czujnik) i odczytać, który rejestr się zmienia.

## Uwaga
Dokładne mapowanie kod liczbowy ↔ tekst wymaga jeszcze korelacji z rejestrami
w czasie rzeczywistym (np. wymusić błąd), ale lista tekstów jest kompletna.
