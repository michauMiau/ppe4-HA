# ppe4-HA
[brand img](brand/icon.png)
Integration for the KOSPEL PPE4 Water heater in Home Assistant.

## Features

- **Sensors**: target temperature, min/max setpoints, limits, current power, operating mode
- **Number entity**: set the target temperature (slider) — written directly to the heater
- Local HTTP polling (30 s), no cloud

## Installation

### HACS (recommended)

[![Open your Home Assistant instance and add the repository in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=michauMiau&repository=ppe4-HA&category=integration)

1. Click the badge above (or **HACS → ⋮ → Custom repositories**)
2. Repository: `michauMiau/ppe4-HA`, category: **Integration**
3. Click **Download** on *KOSPEL PPE4*.
4. Restart Home Assistant.

### Manual

1. Copy `custom_components/kospel_ppe4/` into your HA `config/custom_components/` directory.
2. Restart Home Assistant.

### Add the device

[![Open your Home Assistant instance and start setting up.](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=kospel_ppe4)

Or: *Settings → Devices & Services → Add Integration → **KOSPEL PPE4***.
The config flow requires you to type ip of your heater, it's visible in the app.

### Energy Dashboard

The `Energy (month)` sensor is a `total_increasing` kWh meter and the water sensors
are `total_increasing` liters meters — add them in
*Settings → Dashboards → Energy → Individual devices*.

Protocol details: see [PROTOCOL.md](PROTOCOL.md).

---

## 📶 Jak połączyć podgrzewacz KOSPEL PPE4 z WiFi bez aplikacji (polish guide)

### 1. Tryb konfiguracji na piecu

1. **Przytrzymaj środkowy przycisk** na panelu pieca, aby wejść do menu.
2. Przejdź do menu **KONFIG** (prawy przycisk) i zatwierdź.
3. W menu konfiguracji wybierz pozycję **WIFI**.
4. Wybierz **KONFIG WIFI**, aby rozpocząć zestawienie połączenia — piec przejdzie w tryb parowania
   i wyświetli odliczanie (**300** sekund / „CZEKAJ”). Masz 5 minut na dokończenie konfiguracji.

> 📝 Przy okazji: w menu możesz podejrzeć **numer modułu** (XXXX) — zapisz go, przyda się
> podczas pierwszej konfiguracji w aplikacji KOSPEL PPE4.

### 2. Połącz się z siecią pieca

1. Na telefonie/tablecie/komputerze otwórz ustawienia WiFi i połącz się z siecią o nazwie
   **ppe4_0000xxxx** (nazwa sieci to identyfikator Twojego urządzenia).
2. Hasło do tej sieci to domyślnie **12345678**.

### 3. Konfiguracja przez stronę pieca

1. Otwórz przeglądarkę i wejdź na adres **<http://192.168.8.1>** — otworzy się strona
   *„KOSPEL PPE4 Wi-Fi configuration”* z listą dostępnych sieci (SSID, siła sygnału, kanał).
2. Kliknij **Connect** przy swojej sieci domowej i wpisz w okienku **hasło do swojego WiFi**.
3. Piec połączy się z routerem. Status na wyświetlaczu pieca pokaże siłę sygnału **1–100%**
   (symbol `---` = brak połączenia — wtedy powtórz konfigurację).

### 4. Dodaj do Home Assistant

1. Sprawdź w routerze (lub skanem sieci), jakie IP otrzymał piec.
2. Zainstaluj integrację jak wyżej i podaj ten adres IP. Gotowe! 🎉

> 💡 **Tip:** ustaw w routerze rezerwację DHCP dla pieca, żeby IP się nie zmieniało.
