# Hijacker de Tráfego Web

## O que é um Hijacker?

Um **hijacker** (sequestrador de tráfego) é um software ou técnica que intercepta e redireciona o tráfego de rede de um dispositivo ou sistema.

No contexto deste script (`hijacker_app.py`), trata-se de um hijacker de tráfego web (HTTP e HTTPS) que **redireciona todo o tráfego de saída nas portas 80 (HTTP) e 443 (HTTPS)** para servidores locais.
Esses servidores locais respondem com um redirecionamento HTTP **302** para uma URL específica — neste caso:

➡️ **[https://github.com/Joyce-Ribeiro/SantaClaraPapelaria](https://github.com/Joyce-Ribeiro/SantaClaraPapelaria)**

> **Atenção:** O uso deste tipo de software em redes ou dispositivos sem autorização é **ilegal e antiético**. Use apenas em ambientes controlados e para fins educativos/testes.

---

## Como Funciona?

O hijacker intercepta pacotes TCP destinados às portas **80** e **443** usando regras **NAT** via `iptables`.

Em vez de enviar para o destino original, o tráfego é redirecionado para:

* **Porta 80 →** Servidor HTTP local na porta **8080**
* **Porta 443 →** Servidor HTTPS local na porta **8443** (com certificado *self-signed*)

Esses servidores locais respondem a qualquer requisição com um redirecionamento HTTP **302** para o repositório GitHub especificado.

---

## Limitações

* Funciona **apenas** no tráfego originado no mesmo sistema.
* HTTPS usa certificado *self-signed* → navegadores exibem aviso de segurança.
* Em WSL, pode não afetar navegadores do Windows devido a pilhas de rede separadas.
* Sites com **HSTS** (ex.: Google) podem recusar o redirecionamento ou mostrar erro.

---

## Como Foi Desenvolvido?

* **Linguagem:** Python 3

* **Principais bibliotecas:**

  * `subprocess` → execução de comandos (`openssl`, `iptables`)
  * `threading` → servidores HTTP e HTTPS em paralelo
  * `http.server` → servidor HTTP
  * `ssl` → servidor HTTPS
  * `signal` → interceptar Ctrl+C e finalizar de forma segura

* **Fluxo de desenvolvimento:**

  1. Servidor HTTP simples
  2. Suporte a HTTPS com certificado *self-signed*
  3. Regras `iptables` para hijacking
  4. Logging e tratamento de erros

* **Ambiente de teste:** Ubuntu/WSL2, executado como root.

---

## Passo a Passo de Funcionamento

1. **Verifica permissões** → exige execução como root.
2. **Gera certificado** (*self-signed*) se não existir.
3. **Configura sinais** para finalizar corretamente.
4. **Inicializa servidores:**

   * HTTP na porta 8080
   * HTTPS na porta 8443
5. **Aplica regras `iptables`** redirecionando portas 80 e 443.
6. **Mantém loop principal** até Ctrl+C.
7. **Ao encerrar**, remove as regras e finaliza.

---

## Como Testar

### Requisitos

* Ubuntu ou WSL2
* Python 3
* OpenSSL (`sudo apt install openssl`)
* Permissão de root

### Execução

```bash
sudo python3 hijacker_app.py
```

### Verificar regras do iptables

```bash
sudo iptables -t nat -L -v -n
```

### Teste HTTP

```bash
curl -i http://example.com
```

✅ Esperado: Resposta 302 com `Location` para o GitHub.

### Teste HTTPS

```bash
curl -i -k https://www.google.com
```

✅ Esperado: Resposta 302 com `Location` para o GitHub.

### Teste no navegador (em WSL)

```bash
sudo apt install firefox
firefox https://www.google.com
```

Aceite o aviso de certificado → redirecionamento para o GitHub.

---

## Encerramento

1. Pressione **Ctrl+C** no terminal.
2. Verifique se as regras foram removidas:

```bash
sudo iptables -t nat -L -v -n
```

---

## Dicas

* Problemas com certificado?
  → Delete `selfsigned.*` e execute novamente.
* Em WSL, teste com ferramentas **dentro** do WSL.
* Para gerar executável:

```bash
pyinstaller --onefile \
  --add-data "selfsigned.crt:." \
  --add-data "selfsigned.key:." \
  hijacker_app.py
```

---

⚠ **Aviso Legal:**
Este script deve ser utilizado **apenas** em ambientes de laboratório ou com autorização explícita.
O uso indevido pode configurar crime de invasão ou interceptação de comunicações.
