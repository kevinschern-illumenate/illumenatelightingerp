### ilLumenate Lighting ERP

Custom ERP for ilLumenate Lighting

## Installation

You can install this app using the [bench](https://github.com/frappe/bench) CLI:

```bash
cd $PATH_TO_YOUR_BENCH
bench get-app $URL_OF_THIS_REPO --branch develop
bench install-app custom_erpnext
```

## ilLumenate Configurator Module

The ilLumenate Configurator module provides a fixture configuration engine for LED lighting products.

### Features

- **ILL LED Tape Spec**: Define LED tape specifications linked to ERPNext Items (supports Item Templates with variant attributes)
- **ILL Driver Spec**: Define driver specifications with voltage, dimming protocol, and wattage (supports Item Templates with variant attributes)
- **ILL Fixture Template**: Define fixture templates with endcap options and allowances
- **Configurator Rules Engine**: Calculate manufacturable lengths, run counts, and driver selection
- **Configurator Test Harness**: Internal UI for testing configurations

### Item Templates & Variant Support

The configurator supports linking specs to ERPNext Item Templates (items with variants). When creating specs:

1. **Link to Template**: Set `tape_item` or `driver_item` to an Item Template
2. **Specify Attributes**: In the "Variant Attributes" section, add the attribute values for this spec
3. **Automatic Resolution**: When generating BOMs (future sprint), the system will resolve to the correct Item Variant

Example: If you have an LED Tape template with "Color Temperature" and "CRI" attributes:
- Create a spec linked to the template
- Add variant attributes: Color Temperature = "3000K", CRI = "90"
- The system will resolve this to the specific variant when needed

### Roles

- **Illumenate Admin**: Full access to all configurator DocTypes
- **Illumenate Product Manager**: Create/edit access to configurator DocTypes

### API

#### validate_configuration

Endpoint: `POST /api/method/custom_erpnext.illumenate_configurator.api.validate_configuration`

**Request Parameters:**
- `template_code` (string, required): Fixture template code (e.g., "SH01")
- `tape_spec` (string, required): ILL LED Tape Spec name
- `requested_overall_in` (float, required): Requested overall length in inches
- `dimming_protocol` (string, required): Dimming protocol (0-10V, DALI, DMX, TRIAC, PWM, Other)
- `endcap_item` (string, optional): Endcap Item name. Uses template default if omitted.

**Response (success):**
```json
{
  "inputs": {
    "template_code": "SH01",
    "tape_spec": "TAPE-SPEC-00001",
    "tape_item": "LED-TAPE-24V",
    "requested_overall_in": 50.0,
    "dimming_protocol": "0-10V",
    "endcap_item": "ENDCAP-A",
    "voltage": "24"
  },
  "length": {
    "requested": {"in_raw": 50.0, "in_display_1_16": 50.0, "mm": 1270.0},
    "tape_cut": {"in_raw": 48.5, "in_display_1_16": 48.5, "mm": 1231.9},
    "manufacturable": {"in_raw": 49.25, "in_display_1_16": 49.25, "mm": 1250.95},
    "delta": {"in_raw": 0.75, "in_display_1_16": 0.75, "mm": 19.05},
    "warning": "Length has been rounded down to the nearest tape cut increment..."
  },
  "electrical": {
    "watts_per_ft": 10.0,
    "total_watts": 40.0,
    "runs_count": 1,
    "max_run_ft_by_85w": 8.5
  },
  "driver": {
    "driver_spec": "DRV-SPEC-00001",
    "driver_item": "DRIVER-100W",
    "quantity": 1,
    "usable_watts_each": 80.0,
    "total_usable_watts": 80.0
  },
  "errors": []
}
```

**Response (error):**
```json
{
  "errors": [
    {
      "code": "TEMPLATE_NOT_FOUND",
      "message": "Fixture template 'INVALID' not found.",
      "field": "template_code"
    }
  ]
}
```

### Rules Engine

**Length Computation:**
- Input: inches, Internal math: mm, Output: inches to nearest 1/16"
- E = endcap_allowance_mm_per_side
- A = leader_allowance_mm (15mm default)
- C = tape cut_increment_mm
- L_internal = L_req_mm - 2E - A
- L_tape_cut = floor(L_internal / C) * C
- L_mfg = L_tape_cut + 2E + A

**Run Count (≤85W per run):**
- Total_ft = L_tape_cut_mm / 304.8
- W_total = Total_ft * watts_per_ft
- MaxRun_ft = 85 / watts_per_ft
- runs_count = ceil(Total_ft / MaxRun_ft)

**Driver Selection (80% derating):**
- W_usable = 0.8 * max_wattage
- N_out = ceil(runs_count / outputs_count)
- N_w = ceil(W_total / W_usable)
- N = max(N_out, N_w)
- Ranking: 1) Lowest N, 2) Lowest max_wattage, 3) driver_item name

## Running Tests

Run all tests for this app:

```bash
cd $PATH_TO_YOUR_BENCH
bench run-tests --app custom_erpnext
```

Run only the configurator engine unit tests (no Frappe instance required):

```bash
cd $PATH_TO_YOUR_BENCH/apps/custom_erpnext
python -m pytest custom_erpnext/illumenate_configurator/tests/test_engine.py -v
```

Or using unittest directly:

```bash
cd $PATH_TO_YOUR_BENCH/apps/custom_erpnext
python -m unittest custom_erpnext.illumenate_configurator.tests.test_engine -v
```

## Contributing

This app uses `pre-commit` for code formatting and linting. Please [install pre-commit](https://pre-commit.com/#installation) and enable it for this repository:

```bash
cd apps/custom_erpnext
pre-commit install
```

Pre-commit is configured to use the following tools for checking and formatting your code:

- ruff
- eslint
- prettier
- pyupgrade

## License

MIT
