# Hipóteses de simulação e escopo de integração

## Unidades e horizonte de cálculo

- Potência em kW; energia em kWh; duração em horas.
- A energia entregue pelo veículo no intervalo é potência alocada × duração, limitada pelo pedido informado.
- A demanda de potência do veículo no intervalo é o menor valor entre a potência máxima do veículo e a energia ainda pedida dividida pela duração.
- A potência entregue não pode superar o limite da estação; a importação da rede não pode superar o limite configurado; cada veículo respeita o seu próprio limite.

## Modelo fotovoltaico

A curva fotovoltaica é uma senoide simplificada entre 6h e 18h, com pico de referência ao meio-dia. A potência final é afetada por um fator climático configurável entre 0 e 1. Não usa dados meteorológicos nem produz previsão real.

## Bateria

A bateria possui capacidade energética, SOC inicial, reserva mínima, limite de potência de carga e descarga e eficiência de carga/descarga. O excedente fotovoltaico é usado para carregar a bateria até os limites do modelo. Não ocorre crédito de emissão renovável para energia que já estava armazenada, pois a versão atual não rastreia sua origem.

## Tarifas e emissões

As tarifas e fatores de emissão são didáticos e estão no `SystemConfig`; devem ser identificados como hipóteses em toda apresentação. Não representam proposta de tarifa, fatura, tarifa regulada ou fator de emissão oficial. A linha de referência considera o custo/emissão de fornecer a mesma energia entregue somente pela rede com a tarifa/fator configurados.

## Compatibilidade com GoodWe

O projeto modela conceitualmente modos conhecidos na documentação do carregador GoodWe HCA G2 e uma regra de balanceamento de carga. Não realiza autenticação SEMS, não acessa API privada, não abre comunicação Modbus e não controla equipamentos. Uma integração de produção requer documentação para o modelo e firmware instalados, credenciais/autorização, definição de leitura e escrita, tratamento de falhas, segurança, validação elétrica e testes homologados.
