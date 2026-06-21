# Clean Room Policy

Ceibo AI: la inteligencia argentina que trabaja con vos.

Ceibo Core es el cerebro conversacional, cognitivo y agente de Ceibo AI, capaz de dialogar con humanos de forma natural y ademas operar verticales especializadas.

## Principio

La reimplementacion clean-room separa el analisis autorizado de la
implementacion. Una persona o agente documenta comportamiento observable y
restricciones legales; otra etapa implementa una solucion propia sin copiar
codigo, secretos, recursos protegidos ni expresiones propietarias.

## Controles minimos

- Registrar fuente, licencia y alcance autorizado.
- Separar especificacion funcional de implementacion.
- Evitar copiar nombres internos, codigo, assets o strings propietarios cuando
  no sean necesarios para interoperabilidad legitima.
- Mantener auditoria de decisiones.
- Pedir revision humana/legal para tecnologia protegida.
