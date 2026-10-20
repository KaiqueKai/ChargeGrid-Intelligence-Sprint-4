# Evolução da Sprint 3 para a Sprint 4

## O que foi mantido

- Nome e domínio do projeto ChargeGrid Intelligence.
- Arquitetura modular Python e execução pelo terminal.
- Módulos de geração solar, bateria, regra decisória, tarifação e visualização.
- Continuidade da prova de conceito GoodWe para recarga de veículos elétricos.

## Problemas encontrados na versão da Sprint 3

1. Mistura de unidades: variáveis descritas como kW eram usadas como energia, sem uma duração explícita do intervalo.
2. A redução de potência era um fator global baseado somente na quantidade de veículos, não um rateio sujeito à capacidade individual e à potência total.
3. O caminho normal não armazenava o excedente solar na bateria.
4. A decisão indicava uma fonte predominante, mas não fazia a composição numérica real entre solar, bateria e rede.
5. O custo de recarga aplicava uma tarifa única à sessão mesmo quando a origem da energia era mista.
6. A geração solar incluía aleatoriedade, tornando comparações e evidências de resultado menos reproduzíveis.
7. Não havia suíte de testes automatizados.

## Melhorias implementadas na Sprint 4

- Definição explícita de duração e unidades para potência e energia.
- Despacho real dentro dos limites de estação, rede, potência individual e SOC mínimo da bateria.
- Rateio ponderado entre veículos e cálculo de energia entregue/pendente.
- Eficiência e limites de potência para carga/descarga da bateria.
- Carga da bateria com excedente fotovoltaico.
- Conta mista por fonte energética.
- Comparação explicável entre `PV Priority`, `PV + Battery` e `Fast`.
- Estimativas ambientais conservadoras com hipóteses declaradas.
- Dashboard Streamlit, exportação JSON/CSV, diagrama funcional e relatório de cenário reproduzível.
- Assistente virtual local explicável que responde a perguntas sobre os indicadores da sessão, sem API externa.
- Testes unitários dos limites e balanços principais.

## Limites mantidos de forma transparente

Não se declara conexão física com equipamentos GoodWe nem ganhos medidos no mundo real. O protótipo é uma evolução funcional da simulação da Sprint 3 e identifica explicitamente as etapas necessárias para uma integração real.


O gráfico `docs/dashboard_sprint3_original.png` foi preservado do ZIP de entrada como evidência visual da versão anterior; não é um resultado da Sprint 4.
