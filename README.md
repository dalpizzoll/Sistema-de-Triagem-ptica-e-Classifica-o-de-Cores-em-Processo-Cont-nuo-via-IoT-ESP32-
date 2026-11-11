# 🎨 Sistema de Triagem Óptica e Classificação de Cores em Processo Contínuo via IoT (ESP32)

Este repositório contém o firmware em **MicroPython** para um sistema automatizado de esteira seletora por cor integrado à plataforma **ThingsBoard** via protocolo **MQTT**. 

O sistema realiza a identificação de peças por cor (Vermelho, Verde, Azul) utilizando processamento de frequência óptica, desvio automatizado através de servo-motores e controle de transporte contínuo via motor de passo, monitorado em tempo real com barreira ultrassônica e sensores ópticos reflexivos.

---

## 📌 Visão Geral do Funcionamento

1. **Tracionamento Contínuo:** O motor de passo 28BYJ-48 (com driver ULN2003) mantém a esteira em movimento de acordo com o estado do sistema (`power` e `emergency`).
2. **Detecção de Entrada:** O sensor ultrassônico HC-SR04 identifica a chegada da peça ($\le 7\text{ cm}$) e inicia uma temporização não bloqueante de transporte ($8\text{ segundos}$) até o ponto de leitura.
3. **Análise Cromática:** O sensor TCS230/TCS3200 faz a leitura da frequência dos canais R, G e B por amostragem de pulsos (`time_pulse_us`) e classifica a cor da peça.
4. **Desvio Automatizado:** O servo-motor da respectiva cor é acionado no ângulo de desvio adequado para direcionar a peça para a calha correta.
5. **Confirmação e Reset:** Os sensores reflexivos TCRT5000 monitoram a passagem da peça na calha de destino, desativando o servo e retornando-o à posição de repouso.
6. **Telemetria e Controle Remoto:** O ESP32 envia dados contínuos de status ao ThingsBoard e aceita comandos remotos RPC para controle da operação.

---

## 🛠️ Mapeamento de Hardware e Pinagem (ESP32)

| Componente | Função | Pino ESP32 | Modo / Sinal |
| :--- | :--- | :--- | :--- |
| **Motor de Passo (ULN2003)** | Bobina IN1 | `GPIO 27` | Saída Digital |
| | Bobina IN2 | `GPIO 26` | Saída Digital |
| | Bobina IN3 | `GPIO 25` | Saída Digital |
| | Bobina IN4 | `GPIO 33` | Saída Digital |
| **Ultrassônico (HC-SR04)** | Trigger | `GPIO 14` | Saída Digital |
| | Echo | `GPIO 35` | Entrada Digital |
| **Sensor de Cor (TCS230)** | S0 (Escala 20%) | `GPIO 23` | Saída Digital |
| | S1 (Escala 20%) | `GPIO 22` | Saída Digital |
| | S2 (Seleção Filtro) | `GPIO 21` | Saída Digital |
| | S3 (Seleção Filtro) | `GPIO 19` | Saída Digital |
| | OUT (Frequência) | `GPIO 18` | Entrada Digital |
| **Sensores TCRT5000** | TCRT Azul | `GPIO 17` | Entrada Digital |
| | TCRT Verde | `GPIO 4` | Entrada Digital |
| | TCRT Vermelho | `GPIO 15` | Entrada Digital |
| **Servo-Motores (PWM 50Hz)** | Servo 1 (Azul) | `GPIO 5` | Saída PWM |
| | Servo 2 (Vermelho) | `GPIO 16` | Saída PWM |
| | Servo 3 (Verde) | `GPIO 2` | Saída PWM |

---

## 🌐 Integração IoT (ThingsBoard MQTT & RPC)

### Tópicos MQTT Utilizados

- **Publicação de Telemetria:** `v1/devices/me/telemetry`
- **Assinatura de Comandos RPC:** `v1/devices/me/rpc/request/+`

### Dicionário de Telemetria Enviada

```json
{
  "distancia_cm": 5.4,
  "motor_estado": "EM_MOVIMENTO",
  "power": true,
  "emergency": false,
  "tcrt_blue": 1,
  "tcrt_green": 0,
  "tcrt_red": 1,
  "red": 12,
  "green": 8,
  "blue": 15,
  "unknow": 1
}
```

### Comandos RPC Suportados (Controle Remoto)

| Método RPC | Tipo Parâmetro | Valores Exemplo | Descrição |
| :--- | :--- | :--- | :--- |
| `setPower` | `boolean` | `true` / `false` | Liga ou desliga a operação da esteira |
| `emergencyStop` | `boolean` | `true` / `false` | Parada de emergência imediata do motor |
| `setMotorSpeed` | `integer` | `1` a `15` | Ajusta o atraso (ms) entre passos do motor |

---

## ⚙️ Arquitetura de Software e Não Bloqueio

O firmware foi estruturado sem loops de pausa bloqueantes (`time.sleep`) na malha principal, utilizando temporização relativa baseada em `time.ticks_ms()` e `time.ticks_diff()`. Isso garante que:

- A comunicação MQTT via `cliente.check_msg()` permaneça responsiva para comandos RPC de emergência.
- A amostragem dos sensores ocorra em janelas de tempo paralelas.
- O motor de passo mantenha sua cadência contínua sem interrupções por leitura de sensores.

---

## 🚀 Como Executar

### Pré-requisitos

- Microcontrolador **ESP32** com firmware **MicroPython** instalado.
- Biblioteca `umqtt.robust` disponível na flash.
- Conta/Instância ativa no **ThingsBoard**.

### Passos para Instalação

1. Clone este repositório ou copie o arquivo `.py` principal.
2. Atualize as variáveis de ambiente no código:
   ```python
   WIFI_SSID = "SUA_REDE_WIFI"
   WIFI_PASS = "SUA_SENHA"
   BROKER = "demo.thingsboard.io"
   ACCESS_TOKEN = "SEU_ACCESS_TOKEN_THINGSBOARD"
   ```
3. Realize o upload do código utilizando o **Thonny IDE**, **ampy** ou extensão **Pymakr** no VS Code.
4. Execute o programa e acompanhe os dados via Dashboard no ThingsBoard.
