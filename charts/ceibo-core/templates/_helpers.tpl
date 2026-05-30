{{- define "ceibo-core.name" -}}
ceibo-core
{{- end -}}

{{- define "ceibo-core.labels" -}}
app.kubernetes.io/name: {{ include "ceibo-core.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end -}}
