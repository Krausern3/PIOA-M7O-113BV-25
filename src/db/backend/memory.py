Bases: list = []


def create_bs(name, temp: list[str]):
    temporary = [name, temp, []]
    Bases.append(temporary)


def delete_bs(n):
    Bases.remove(Bases[n])


def return_bs():
    return Bases


def get_tmp(number_of_base):
    return Bases[number_of_base][1].copy()


def create_rcd(
    number_of_base,
    values: list,
):

    temp = Bases[number_of_base][1]

    if len(values) != len(temp):
        raise ValueError(f"Ожидается {len(temp)} значений, получено {len(values)}.")

    if any(record[0] == values[0] for record in Bases[number_of_base][2]):
        raise ValueError(f"Запись с id={values[0]} уже существует.")

    cleaned_values = []
    for value in values:
        if isinstance(value, str):
            cleaned_values.append(value.strip())
        else:
            cleaned_values.append(value)

    new_record = tuple(cleaned_values)
    Bases[number_of_base][2].append(new_record)
    return new_record


def select_rcd(
    number_of_base,
    filters: list = None,
):
    if filters is None:
        filters = []

    records = Bases[number_of_base][2]
    if not filters:
        return records.copy()

    result = []

    for i in records:
        flag = True
        for j in range(len(filters)):
            if not (filters[j] is None or filters[j] == "" or filters[j] == i[j]):
                flag = False
                break
        if flag:
            result.append(i)

    return result


def update_rcd(
    number_of_base,
    record_index: int,  # Номер таблицы
    new_values: list,
):
    records = Bases[number_of_base][2]

    if record_index >= len(records):
        raise ValueError(f"Запись с индексом {record_index} не существует.")

    old_record = records[record_index]
    new_record_list = list(old_record)

    for j in range(min(len(new_values), len(new_record_list))):
        if new_values[j] is not None:
            if isinstance(new_values[j], str):
                new_record_list[j] = new_values[j].strip()
            else:
                new_record_list[j] = new_values[j]

    Bases[number_of_base][2][record_index] = tuple(new_record_list)


def delete_rcd(number_of_base, result, n=0):
    if n >= len(result):
        return False

    try:
        Bases[number_of_base][2].remove(result[n])
        return True
    except ValueError:
        return False
