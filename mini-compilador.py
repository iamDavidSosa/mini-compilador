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
        palabras = re.findall(r'\b\w+\b|[\+\-\*/%=(){},;\[\]]|".*?"|==|!=|<=|>=|&&|\|\||!', linea)
        for palabra in palabras:
            if re.match(r'\b(int|double|string|bool|if|else|for|while|try|catch|finally|switch|case|default|break|do|using|class|static|void|Main|return|public|private|protected)\b', palabra):
                tokens.append(('PALABRA_CLAVE', palabra, num_linea))
            elif re.match(r'\b(true|false)\b', palabra):
                tokens.append(('VALOR_BOOL', palabra, num_linea))
            elif re.match(r'\b\d+\.?\d*\b', palabra):
                tokens.append(('NUMERO', palabra, num_linea))
            elif re.match(r'\b\w+\b', palabra):
                tokens.append(('IDENTIFICADOR', palabra, num_linea))
            elif re.match(r'[\+\-\*/%=]', palabra):
                tokens.append(('OPERADOR_ARITMETICO', palabra, num_linea))
            elif re.match(r'==|!=|<=|>=|<|>', palabra):
                tokens.append(('OPERADOR_RELACIONAL', palabra, num_linea))
            elif re.match(r'&&|\|\||!', palabra):
                tokens.append(('OPERADOR_LOGICO', palabra, num_linea))
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
                return False, f"Error de sintaxis: Símbolo de cierre '{token[1]}' '{token[1]}' no coincide con '{apertura}' en línea {token[2]}"
    if stack:
        return False, f"Error de sintaxis: Símbolo de apertura '{stack[-1][0]}' en línea {stack[-1][1]} no fue cerrado"
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
                            ast.append(('ERROR', f"Se esperaba un valor después de '=' en línea {token[2]}"))
                            i += 3
                    else:
                        i += 2
                    ast.append(('DECLARACION', tipo, nombre, valor))
                else:
                    ast.append(('ERROR', f"Se esperaba un identificador después de '{token[1]}' en línea {token[2]}"))
                    i += 1
            elif token[1] == 'if':
                # Condicional if
                if i + 1 < len(tokens) and tokens[i + 1][1] == '(':
                    condicion = []
                    parentesis_balance = 0
                    start_index = i + 2
                    while start_index < len(tokens):
                        if tokens[start_index][1] == '(':
                            parentesis_balance += 1
                        elif tokens[start_index][1] == ')':
                            if parentesis_balance == 0:
                                break
                            else:
                                parentesis_balance -= 1
                        condicion.append(tokens[start_index][1])
                        start_index += 1
                    if start_index < len(tokens) and tokens[start_index][1] == ')':
                        ast.append(('IF', ' '.join(condicion)))
                        i = start_index + 1
                    else:
                        ast.append(('ERROR', f"Se esperaba ')' para la condición del 'if' en línea {token[2]}"))
                        i += 1
                else:
                    ast.append(('ERROR', f"Se esperaba '(' después de 'if' en línea {token[2]}"))
                    i += 1
            elif token[1] == 'for':
                # Bucle for
                if i + 1 < len(tokens) and tokens[i + 1][1] == '(':
                    contenido_parentesis = []
                    parentesis_balance = 0
                    start_index = i + 2
                    while start_index < len(tokens):
                        if tokens[start_index][1] == '(':
                            parentesis_balance += 1
                        elif tokens[start_index][1] == ')':
                            if parentesis_balance == 0:
                                break
                            else:
                                parentesis_balance -= 1
                        contenido_parentesis.append(tokens[start_index][1])
                        start_index += 1
                    if start_index < len(tokens) and tokens[start_index][1] == ')':
                        partes_for = ' '.join(contenido_parentesis).split(';')
                        if len(partes_for) == 3:
                            inicio = partes_for[0].strip()
                            condicion = partes_for[1].strip()
                            incremento = partes_for[2].strip()
                            ast.append(('FOR', inicio, condicion, incremento))
                            i = start_index + 1
                        else:
                            ast.append(('ERROR', f"Estructura incorrecta en el 'for' en línea {token[2]}"))
                            i += 1
                    else:
                        ast.append(('ERROR', f"Se esperaba ')' para la definición del 'for' en línea {token[2]}"))
                        i += 1
                else:
                    ast.append(('ERROR', f"Se esperaba '(' después de 'for' en línea {token[2]}"))
                    i += 1
            elif token[1] == 'return':
                if i + 1 < len(tokens) and tokens[i+1][0] != 'SIMBOLO' and tokens[i+1][1] != ';':
                    ast.append(('RETURN', tokens[i+1][1]))
                    i += 2
                else:
                    ast.append(('RETURN', None))
                    i += 1
            elif token[1] in ['public', 'private', 'protected', 'static', 'void', 'class']:
                ast.append(('MODIFICADOR', token[1]))
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
    python_code =[]
    indentacion_stack = [0]
    en_clase = False
    en_switch = False
    variable_switch = None
    en_funcion = False
    nombre_funcion = None
    nombre_clase = None
    case_agrupado = False
    valores_case_agrupado =[]
    indentacion_switch = 0 # Para recordar la indentación del switch

    for linea in lineas:
        linea = re.sub(r'//.*', '', linea)
        linea = re.sub(r'/\*.*?\*/', '', linea, flags=re.DOTALL)
        linea = linea.strip()
        if not linea:
            continue

        if linea == 'using System;':
            continue
        elif linea.startswith('using '):
            namespace = linea.split('using ')[1].rstrip(';')
            python_code.append(f'import {namespace}')
            continue

        if 'class ' in linea:
            nombre_clase = linea.split('class ')[1].split('{')[0].strip()
            python_code.append(f'class {nombre_clase}:')
            en_clase = True
            indentacion_stack.append(indentacion_stack[-1] + 4)
            continue

        if re.match(r'^(public|private|protected)?\s*(static)?\s*void\s+Main\(', linea):
            python_code.append(' ' * indentacion_stack[-1] + '@staticmethod')
            python_code.append(' ' * indentacion_stack[-1] + 'def Main():')
            en_funcion = True
            indentacion_stack.append(indentacion_stack[-1] + 4)
            continue
        elif re.match(r'^(public|private|protected)?\s*(static)?\s*\w+\s+\w+\s*\(', linea) and '{' in linea:
            match = re.match(r'^(public|private|protected)?\s*(static)?\s*(\w+)\s+(\w+)\s*\(', linea)
            if match:
                nombre_funcion = match.group(4)
                python_code.append(' ' * indentacion_stack[-1] + f'def {nombre_funcion}():')
                en_funcion = True
                indentacion_stack.append(indentacion_stack[-1] + 4)
                continue

        if '{' in linea:
            indentacion_stack.append(indentacion_stack[-1] + 4)
            continue
        if '}' in linea:
            indentacion_stack.pop()
            if en_switch:
                en_switch = False
                variable_switch = None
                case_agrupado = False
                valores_case_agrupado =[]
            elif en_clase:
                en_clase = False
            elif en_funcion:
                en_funcion = False
                nombre_funcion = None
            continue

        indentacion_actual = indentacion_stack[-1]

        if 'Console.WriteLine' in linea:
            contenido = linea.split('(', 1)[1].rsplit(')', 1)[0].strip()
            if '+' in contenido and ('"' in contenido):
                partes = [p.strip() for p in re.split(r'\s*\+\s*', contenido)]
                python_print_args =[]
                for parte in partes:
                    if not parte.startswith('"') or not parte.endswith('"'):
                        python_print_args.append(f'str({parte})')
                    else:
                        python_print_args.append(parte)
                python_code.append(' ' * indentacion_actual + f'print({", ".join(python_print_args)})')
            elif contenido.startswith('"') and contenido.endswith('"'):
                python_code.append(' ' * indentacion_actual + f'print("{contenido[1:-1]}")')
            else:
                python_code.append(' ' * indentacion_actual + f'print({contenido})')
        elif re.match(r'^(int|double|string|bool)\s+\w+\s*(=\s*[^;]+)?;$', linea):
            partes = linea.split()
            tipo = partes[0]
            nombre_var = partes[1].rstrip(';')
            valor = 'None'
            if '=' in linea:
                valor = linea.split('=')[1].rstrip(';').strip()
                if valor == 'true':
                    valor = 'True'
                elif valor == 'false':
                    valor = 'False'
            python_code.append(' ' * indentacion_actual + f'{nombre_var} = {valor}')
        elif 'if (' in linea:
            condicion = linea.split('(', 1)[1].split(')', 1)[0].strip()
            condicion = condicion.replace('true', 'True').replace('false', 'False')
            python_code.append(' ' * indentacion_actual + f'if {condicion}:')
            indentacion_stack.append(indentacion_actual + 4)
        elif 'else if (' in linea:
            condicion = linea.split('(', 1)[1].split(')', 1)[0].strip()
            condicion = condicion.replace('true', 'True').replace('false', 'False')
            python_code.append(' ' * (indentacion_actual - 4) + f'elif {condicion}:')
        elif 'else' in linea:
            python_code.append(' ' * (indentacion_actual - 4) + 'else:')
        elif 'switch (' in linea:
            variable_switch = linea.split('(', 1)[1].split(')', 1)[0].strip()
            en_switch = True
            python_code.append(' ' * indentacion_actual + f'# switch ({variable_switch})')
            indentacion_switch = indentacion_actual # Guardar la indentación del switch
            indentacion_stack.append(indentacion_actual + 4) # Aumentar la indentación para el contenido del switch
            case_agrupado = False
            valores_case_agrupado =[]
            primer_case = True
        elif linea.startswith('case ') and en_switch:
            valor = linea.split()[1].rstrip(':').strip()
            indentacion_case = indentacion_switch + 4 # Indentación para el contenido del case
            if case_agrupado:
                valores_case_agrupado.append(f'{variable_switch} == {valor}')
            else:
                if primer_case:
                    python_code.append(' ' * indentacion_switch + f'if {variable_switch} == {valor}:')
                    primer_case = False
                else:
                    python_code.append(' ' * indentacion_switch + f'elif {variable_switch} == {valor}:')
                case_agrupado = False
        elif linea == 'case' and en_switch: # Para manejar cases múltiples seguidos
            case_agrupado = True
            valor = linea.split()[1].rstrip(':').strip()
            valores_case_agrupado.append(f'{variable_switch} == {valor}')
        elif linea.startswith('default:') and en_switch:
            if valores_case_agrupado:
                python_code.append(' ' * indentacion_switch + f'elif {" or ".join(valores_case_agrupado)}:')
            else:
                python_code.append(' ' * indentacion_switch + 'else:')
            case_agrupado = False
            valores_case_agrupado =[]
        elif 'break;' in linea and en_switch:
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
                elif '<=' in condicion:
                    limite = condicion.split('<=')[1].strip() + " + 1" # Approximation
                elif '>=' in condicion:
                    limite = condicion.split('>=')[1].strip() # Needs more complex handling
                else:
                    limite = condicion
                python_code.append(' ' * indentacion_actual + f'for {var_control} in range({valor_inicial}, int({limite})) :')
                indentacion_stack.append(indentacion_actual + 4)
        elif 'while (' in linea:
            condicion = linea.split('(', 1)[1].split(')', 1)[0].strip()
            condicion = condicion.replace('true', 'True').replace('false', 'False')
            python_code.append(' ' * indentacion_actual + f'while {condicion}:')
            indentacion_stack.append(indentacion_actual + 4)
        elif '++;' in linea:  # Manejar incremento (contador++;)
            variable = linea.split('++;')[0].strip()
            python_code.append(' ' * indentacion_actual + f'{variable} += 1')
        elif '--;' in linea:  # Manejar decremento (contador--;)
            variable = linea.split('--;')[0].strip()
            python_code.append(' ' * indentacion_actual + f'{variable} -= 1')
        elif 'return ' in linea:
            valor_retorno = linea.split('return ')[1].rstrip(';')
            python_code.append(' ' * indentacion_actual + f'return {valor_retorno}')
        else:
            linea = linea.replace('true', 'True').replace('false', 'False')
            python_code.append(' ' * indentacion_actual + linea)

    # Agregar una llamada a Main() si existe
    if 'def Main(' in '\n'.join(python_code) and nombre_clase:
        python_code.append(f'\nif __name__ == "__main__":\n    {nombre_clase}.Main()')
    elif 'def Main(' in '\n'.join(python_code):
        python_code.append(f'\nif __name__ == "__main__":\n    Main()')

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
frame_principal.pack(pady=20, padx=20, fill="both", expand=True)

# Frame para la parte superior (entrada C# y ejecución)
frame_superior = Frame(frame_principal, bg="#f0f0f0")
frame_superior.pack(side="top", fill="x")

# Columna izquierda: Entrada de Código C#
frame_entrada_csharp = Frame(frame_superior, bg="#f0f0f0")
frame_entrada_csharp.pack(side="left", fill="both", expand=True, padx=10)

label_entrada = Label(frame_entrada_csharp, text="Código C#:", bg="#f0f0f0", fg="#333333")
label_entrada.pack(pady=5)

texto_entrada = Text(frame_entrada_csharp, height=15, width=50, bg="white", fg="#333333", wrap="none")
texto_entrada.pack(fill="both", expand=True)
scrollbar_entrada_vert = Scrollbar(frame_entrada_csharp, orient=VERTICAL, command=texto_entrada.yview)
scrollbar_entrada_vert.pack(side=RIGHT, fill=Y)
texto_entrada.configure(yscrollcommand=scrollbar_entrada_vert.set)

# Columna derecha: Ejecución de Python
frame_ejecucion = Frame(frame_superior, bg="#f0f0f0")
frame_ejecucion.pack(side="right", fill="both", expand=True, padx=10)

boton_ejecutar = Button(frame_ejecucion, text="Ejecutar Código Python", command=ejecutar_codigo_python, bg="#4CAF50", fg="white", relief="flat")
boton_ejecutar.pack(pady=10, fill="x")

label_resultado = Label(frame_ejecucion, text="Resultado Final:", bg="#f0f0f0", fg="#333333")
label_resultado.pack(pady=5)

texto_resultado = Text(frame_ejecucion, height=12, width=50, bg="white", fg="#333333", wrap="none")
texto_resultado.pack(fill="both", expand=True)
scrollbar_resultado_vert = Scrollbar(frame_ejecucion, orient=VERTICAL, command=texto_resultado.yview)
scrollbar_resultado_vert.pack(side=RIGHT, fill=Y)
texto_resultado.configure(yscrollcommand=scrollbar_resultado_vert.set)

# Frame para los resultados (en forma de columnas)
frame_resultados = Frame(frame_principal, bg="#f0f0f0")
frame_resultados.pack(side="bottom", fill="both", expand=True)

# Columna 1: Tokens
frame_tokens = Frame(frame_resultados, bg="#f0f0f0")
frame_tokens.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
frame_resultados.grid_columnconfigure(0, weight=1)

label_tokens = Label(frame_tokens, text="Tokens:", bg="#f0f0f0", fg="#333333")
label_tokens.pack(pady=5)

texto_tokens = Text(frame_tokens, height=10, width=40, bg="white", fg="#333333", wrap="none")
texto_tokens.pack(fill="both", expand=True)
scrollbar_tokens_vert = Scrollbar(frame_tokens, orient=VERTICAL, command=texto_tokens.yview)
scrollbar_tokens_vert.pack(side=RIGHT, fill=Y)
texto_tokens.configure(yscrollcommand=scrollbar_tokens_vert.set)
boton_tokens = Button(frame_tokens, text="Mostrar Tokens", command=mostrar_tokens, bg="#4CAF50", fg="white", relief="flat")
boton_tokens.pack(pady=5, fill="x")

# Columna 2: Parsed AST
frame_ast = Frame(frame_resultados, bg="#f0f0f0")
frame_ast.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
frame_resultados.grid_columnconfigure(1, weight=1)

label_ast = Label(frame_ast, text="Parsed AST:", bg="#f0f0f0", fg="#333333")
label_ast.pack(pady=5)

texto_ast = Text(frame_ast, height=10, width=40, bg="white", fg="#333333", wrap="none")
texto_ast.pack(fill="both", expand=True)
scrollbar_ast_vert = Scrollbar(frame_ast, orient=VERTICAL, command=texto_ast.yview)
scrollbar_ast_vert.pack(side=RIGHT, fill=Y)
texto_ast.configure(yscrollcommand=scrollbar_ast_vert.set)
boton_ast = Button(frame_ast, text="Mostrar AST", command=mostrar_ast, bg="#4CAF50", fg="white", relief="flat")
boton_ast.pack(pady=5, fill="x")

# Columna 3: Generated Code (Python)
frame_codigo_generado = Frame(frame_resultados, bg="#f0f0f0")
frame_codigo_generado.grid(row=0, column=2, padx=10, pady=10, sticky="nsew")
frame_resultados.grid_columnconfigure(2, weight=1)

label_codigo_generado = Label(frame_codigo_generado, text="Código Generado (Python):", bg="#f0f0f0", fg="#333333")
label_codigo_generado.pack(pady=5)

texto_codigo_generado = Text(frame_codigo_generado, height=10, width=40, bg="white", fg="#333333", wrap="none")
texto_codigo_generado.pack(fill="both", expand=True)
scrollbar_codigo_generado_vert = Scrollbar(frame_codigo_generado, orient=VERTICAL, command=texto_codigo_generado.yview)
scrollbar_codigo_generado_vert.pack(side=RIGHT, fill=Y)
texto_codigo_generado.configure(yscrollcommand=scrollbar_codigo_generado_vert.set)
boton_generar_codigo = Button(frame_codigo_generado, text="Generar Código Python", command=mostrar_codigo_generado, bg="#4CAF50", fg="white", relief="flat")
boton_generar_codigo.pack(pady=5, fill="x")

# Configurar el peso de las filas para que se expandan correctamente
frame_resultados.grid_rowconfigure(0, weight=1)

root.mainloop()