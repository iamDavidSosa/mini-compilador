import re
import io
import sys
from tkinter import Tk, Text, Button, Label, Frame, END, Scrollbar, VERTICAL, RIGHT, Y, messagebox

# Analizador Léxico
def lexico(entrada):
    tokens = []
    lineas = entrada.split('\n')
    for num_linea, linea in enumerate(lineas, start=1):
        linea = re.sub(r'//.*', '', linea)
        linea = re.sub(r'/\*.*?\*/', '', linea, flags=re.DOTALL)
        palabras = re.findall(r'\b\w+\b|[\+\-\*/%=(){},;\[\]]|".*?"', linea)
        for palabra in palabras:
            if re.match(r'\b(int|double|string|bool|if|else|for|while|try|catch|finally|switch|case|default|break|do|using|class|static|void|Main)\b', palabra):
                tokens.append(('PALABRA_CLAVE', palabra, num_linea))
            elif re.match(r'\b(true|false)\b', palabra):
                tokens.append(('VALOR_BOOL', palabra, num_linea))
            elif re.match(r'\b\d+\.?\d*\b', palabra):
                tokens.append(('NUMERO', palabra, num_linea))
            elif re.match(r'\b\w+\b', palabra):
                tokens.append(('IDENTIFICADOR', palabra, num_linea))
            elif re.match(r'[\+\-\*/%=]', palabra):
                tokens.append(('OPERADOR', palabra, num_linea))
            elif re.match(r'[{}();,\[\]]', palabra):
                tokens.append(('SIMBOLO', palabra, num_linea))
            elif re.match(r'^".*"$', palabra):
                tokens.append(('TEXTO', palabra, num_linea))
            else:
                tokens.append(('DESCONOCIDO', palabra, num_linea))
    return tokens

# Analizador Sintáctico
def sintactico(tokens):
    stack = []
    for token in tokens:
        if token[1] in ['{', '(', '[']:
            stack.append((token[1], token[2]))
        elif token[1] in ['}', ')', ']']:
            if not stack:
                return False, f"Error de sintaxis: Símbolo de cierre '{token[1]}' sin apertura en línea {token[2]}"
            apertura, linea_apertura = stack.pop()
            if (apertura == '{' and token[1] != '}') or \
               (apertura == '(' and token[1] != ')') or \
               (apertura == '[' and token[1] != ']'):
                return False, f"Error de sintaxis: Símbolo de cierre '{token[1]}' no coincide con '{apertura}' en línea {token[2]}"
    if stack:
        return False, f"Error de sintaxis: Símbolo de apertura '{stack[-1][0]}' sin cierre en línea {stack[-1][1]}"
    return True, ""

# Generar AST
def generar_ast(tokens):
    ast = []
    i = 0
    while i < len(tokens):
        token = tokens[i]
        if token[0] == 'PALABRA_CLAVE':
            if token[1] in ['int', 'double', 'string', 'bool']:
                # Declaración de variable
                if i + 1 < len(tokens) and tokens[i + 1][0] == 'IDENTIFICADOR':
                    tipo = token[1]
                    nombre = tokens[i + 1][1]
                    valor = None
                    if i + 2 < len(tokens) and tokens[i + 2][1] == '=':
                        if i + 3 < len(tokens):
                            valor = tokens[i + 3][1]
                            i += 4
                        else:
                            i += 3
                    else:
                        i += 2
                    ast.append(('DECLARACION', tipo, nombre, valor))
                else:
                    i += 1
            elif token[1] == 'if':
                # Condicional if
                if i + 2 < len(tokens) and tokens[i + 1][1] == '(':
                    condicion = tokens[i + 2][1]
                    ast.append(('IF', condicion))
                    i += 4
                else:
                    i += 1
            elif token[1] == 'for':
                # Bucle for
                if i + 2 < len(tokens) and tokens[i + 1][1] == '(':
                    inicio = tokens[i + 2][1]
                    if i + 4 < len(tokens):
                        condicion = tokens[i + 4][1]
                        if i + 6 < len(tokens):
                            incremento = tokens[i + 6][1]
                            ast.append(('FOR', inicio, condicion, incremento))
                            i += 8
                        else:
                            i += 6
                    else:
                        i += 4
                else:
                    i += 1
            else:
                i += 1
        else:
            i += 1
    return ast

# Mostrar AST
def mostrar_ast():
    entrada = texto_entrada.get("1.0", END).strip()
    tokens = lexico(entrada)
    sintaxis_valida, mensaje_sintaxis = sintactico(tokens)
    if not sintaxis_valida:
        texto_ast.delete("1.0", END)
        texto_ast.insert("1.0", f"Error de sintaxis:\n{mensaje_sintaxis}")
    else:
        ast = generar_ast(tokens)
        texto_ast.delete("1.0", END)
        texto_ast.insert("1.0", "AST generado:\n" + "\n".join(str(nodo) for nodo in ast))

# Traductor a Python
def traducir_a_python(entrada):
    lineas = entrada.split('\n')
    python_code = []
    indentacion_stack = [0]
    en_clase = False
    en_switch = False
    variable_switch = None
    en_funcion = False
    nombre_funcion = None

    for linea in lineas:
        linea = re.sub(r'//.*', '', linea)
        linea = re.sub(r'/\*.*?\*/', '', linea, flags=re.DOTALL)
        linea = linea.strip()
        if not linea:
            continue

        if 'class ' in linea:
            nombre_clase = linea.split('class ')[1].split('{')[0].strip()
            python_code.append(f'class {nombre_clase}:')
            en_clase = True
            indentacion_stack.append(indentacion_stack[-1] + 4)
            continue

        if re.match(r'\b(public|private|protected|static|void|int|double|string|bool)\b', linea):
            match = re.match(r'\b(?:public|private|protected|static)?\s*(?:void|int|double|string|bool)\s+(\w+)\s*\(([^)]*)\)', linea)
            if match:
                nombre_funcion = match.group(1)
                parametros = match.group(2)
                parametros_python = []
                for param in parametros.split(','):
                    if param.strip():
                        nombre_param = param.strip().split()[-1]
                        parametros_python.append(nombre_param)
                parametros_python = ', '.join(parametros_python)
                python_code.append(' ' * indentacion_stack[-1] + f'def {nombre_funcion}({parametros_python}):')
                en_funcion = True
                indentacion_stack.append(indentacion_stack[-1] + 4)
                continue

        if 'static void Main()' in linea or 'using ' in linea:
            continue

        if '{' in linea:
            indentacion_stack.append(indentacion_stack[-1] + 4)
            continue
        if '}' in linea:
            if en_clase:
                indentacion_stack.pop()
                en_clase = False
            elif en_switch:
                indentacion_stack.pop()
                en_switch = False
                variable_switch = None
            elif en_funcion:
                indentacion_stack.pop()
                en_funcion = False
                nombre_funcion = None
            else:
                indentacion_stack.pop()
            continue

        indentacion_actual = indentacion_stack[-1]

        if 'Console.WriteLine' in linea:
            contenido = linea.split('(', 1)[1].rsplit(')', 1)[0].strip()
            if contenido.startswith('"') and contenido.endswith('"'):
                python_code.append(' ' * indentacion_actual + f'print("{contenido[1:-1]}")')
            else:
                python_code.append(' ' * indentacion_actual + f'print({contenido})')
        elif 'int ' in linea or 'double ' in linea or 'string ' in linea or 'bool ' in linea:
            partes = linea.split()
            nombre_var = partes[1].replace(';', '')
            valor = 'None'
            if '=' in linea:
                valor = linea.split('=')[1].replace(';', '').strip()
                if valor == 'true':
                    valor = 'True'
                elif valor == 'false':
                    valor = 'False'
            python_code.append(' ' * indentacion_actual + f'{nombre_var} = {valor}')
        elif 'if (' in linea:
            condicion = linea.split('(')[1].split(')')[0].strip()
            condicion = condicion.replace('true', 'True').replace('false', 'False')
            python_code.append(' ' * indentacion_actual + f'if {condicion}:')
            indentacion_stack.append(indentacion_actual + 4)
        elif 'else if (' in linea:
            condicion = linea.split('(')[1].split(')')[0].strip()
            condicion = condicion.replace('true', 'True').replace('false', 'False')
            python_code.append(' ' * (indentacion_actual - 4) + f'elif {condicion}:')
        elif 'else' in linea:
            python_code.append(' ' * (indentacion_actual - 4) + 'else:')
        elif 'switch (' in linea:
            variable_switch = linea.split('(')[1].split(')')[0].strip()
            en_switch = True
            python_code.append(' ' * indentacion_actual + f'# switch ({variable_switch})')
            indentacion_stack.append(indentacion_actual + 4)
        elif 'case ' in linea and en_switch:
            valor = linea.split()[1].replace(':', '').strip()
            if 'case ' in linea and 'default' not in linea:
                if python_code and python_code[-1].strip().startswith('if'):
                    python_code.append(' ' * (indentacion_actual - 4) + f'elif {variable_switch} == {valor}:')
                else:
                    python_code.append(' ' * (indentacion_actual - 4) + f'if {variable_switch} == {valor}:')
            indentacion_stack.append(indentacion_actual)
        elif 'default:' in linea and en_switch:
            python_code.append(' ' * (indentacion_actual - 4) + 'else:')
        elif 'break;' in linea:
            continue
        elif 'for (' in linea:
            contenido_for = linea.split('(', 1)[1].split(')', 1)[0].strip()
            partes = contenido_for.split(';')
            if len(partes) == 3:
                inicio = partes[0].strip()
                condicion = partes[1].strip()
                incremento = partes[2].strip()
                if 'int ' in inicio:
                    inicio = inicio.replace('int ', '').strip()
                var_control, valor_inicial = inicio.split('=')
                var_control = var_control.strip()
                valor_inicial = valor_inicial.strip()
                if '++' in incremento:
                    incremento = f"{var_control} += 1"
                elif '--' in incremento:
                    incremento = f"{var_control} -= 1"
                if '<' in condicion:
                    limite = condicion.split('<')[1].strip()
                elif '>' in condicion:
                    limite = condicion.split('>')[1].strip()
                else:
                    limite = condicion
                python_code.append(' ' * indentacion_actual + f'for {var_control} in range({valor_inicial}, {limite}):')
                indentacion_stack.append(indentacion_actual + 4)
        elif 'while (' in linea:
            condicion = linea.split('(')[1].split(')')[0].strip()
            python_code.append(' ' * indentacion_actual + f'while {condicion}:')
            indentacion_stack.append(indentacion_actual + 4)
        elif '++;' in linea:  # Manejar incremento (contador++;)
            variable = linea.split('++;')[0].strip()
            python_code.append(' ' * indentacion_actual + f'{variable} += 1')
        elif '--;' in linea:  # Manejar decremento (contador--;)
            variable = linea.split('--;')[0].strip()
            python_code.append(' ' * indentacion_actual + f'{variable} -= 1')
        else:
            linea = linea.replace('true', 'True').replace('false', 'False')
            python_code.append(' ' * indentacion_actual + linea)

    # Agregar una llamada a Main() si existe
    if 'def Main(' in '\n'.join(python_code):
        python_code.append('\nMain()')

    return '\n'.join(python_code)

# Mostrar Tokens
def mostrar_tokens():
    entrada = texto_entrada.get("1.0", END).strip()
    tokens = lexico(entrada)
    texto_tokens.delete("1.0", END)
    texto_tokens.insert("1.0", "\n".join(str(token) for token in tokens))

# Mostrar Código Generado
def mostrar_codigo_generado():
    entrada = texto_entrada.get("1.0", END).strip()
    codigo_python = traducir_a_python(entrada)
    texto_codigo_generado.delete("1.0", END)
    texto_codigo_generado.insert("1.0", codigo_python)

# Ejecutar Código Python
def ejecutar_codigo_python():
    codigo_python = texto_codigo_generado.get("1.0", END).strip()
    try:
        # Capturar la salida de exec
        output_capture = io.StringIO()
        sys.stdout = output_capture
        exec(codigo_python)
        sys.stdout = sys.__stdout__
        resultado = output_capture.getvalue()
        if resultado:
            texto_resultado.delete("1.0", END)
            texto_resultado.insert("1.0", resultado)
        else:
            texto_resultado.delete("1.0", END)
            texto_resultado.insert("1.0", "El código se ejecutó correctamente, pero no hubo salida.")
    except Exception as e:
        texto_resultado.delete("1.0", END)
        texto_resultado.insert("1.0", f"Error al ejecutar el código:\n{str(e)}")

# Interfaz gráfica
root = Tk()
root.title("Mini Compilador: C# a Python")
root.configure(bg="#f0f0f0")

frame_principal = Frame(root, bg="#f0f0f0")
frame_principal.pack(pady=10)

# Entrada de Código C#
label_entrada = Label(frame_principal, text="Código C#:", bg="#f0f0f0", fg="#333333")
label_entrada.grid(row=0, column=0, sticky="w")

texto_entrada = Text(frame_principal, width=60, height=10, bg="white", fg="#333333", wrap="none")
texto_entrada.grid(row=1, column=0, padx=5, pady=5)

# Tokens
label_tokens = Label(frame_principal, text="Tokens:", bg="#f0f0f0", fg="#333333")
label_tokens.grid(row=2, column=0, sticky="w")

texto_tokens = Text(frame_principal, width=60, height=5, bg="white", fg="#333333", wrap="none")
texto_tokens.grid(row=3, column=0, padx=5, pady=5)

# Parsed AST
label_ast = Label(frame_principal, text="Parsed AST:", bg="#f0f0f0", fg="#333333")
label_ast.grid(row=4, column=0, sticky="w")

texto_ast = Text(frame_principal, width=60, height=5, bg="white", fg="#333333", wrap="none")
texto_ast.grid(row=5, column=0, padx=5, pady=5)

# Código Generado (Python)
label_codigo_generado = Label(frame_principal, text="Código Generado (Python):", bg="#f0f0f0", fg="#333333")
label_codigo_generado.grid(row=6, column=0, sticky="w")

texto_codigo_generado = Text(frame_principal, width=60, height=10, bg="white", fg="#333333", wrap="none")
texto_codigo_generado.grid(row=7, column=0, padx=5, pady=5)

# Resultado Final
label_resultado = Label(frame_principal, text="Resultado Final:", bg="#f0f0f0", fg="#333333")
label_resultado.grid(row=8, column=0, sticky="w")

texto_resultado = Text(frame_principal, width=60, height=5, bg="white", fg="#333333", wrap="none")
texto_resultado.grid(row=9, column=0, padx=5, pady=5)

# Botones
boton_tokens = Button(frame_principal, text="Mostrar Tokens", command=mostrar_tokens, bg="#4CAF50", fg="white", relief="flat")
boton_tokens.grid(row=10, column=0, pady=5, sticky="ew")

boton_ast = Button(frame_principal, text="Mostrar AST", command=mostrar_ast, bg="#4CAF50", fg="white", relief="flat")
boton_ast.grid(row=11, column=0, pady=5, sticky="ew")

boton_generar_codigo = Button(frame_principal, text="Generar Código Python", command=mostrar_codigo_generado, bg="#4CAF50", fg="white", relief="flat")
boton_generar_codigo.grid(row=12, column=0, pady=5, sticky="ew")

boton_ejecutar = Button(frame_principal, text="Ejecutar Código Python", command=ejecutar_codigo_python, bg="#4CAF50", fg="white", relief="flat")
boton_ejecutar.grid(row=13, column=0, pady=5, sticky="ew")

root.mainloop()