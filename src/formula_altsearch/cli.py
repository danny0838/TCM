import argparse

from . import __version__, searcher


def parse_input_item(input_str):
    for i in range(len(input_str) - 1, -1, -1):
        if not input_str[i].isdigit() and input_str[i] != '.':
            return input_str[:i + 1].strip(), float(input_str[i + 1:])
    return None, None


def adjust_target_composition_for_dosage(target_composition, input_dosage):
    adjusted_target_composition = {}
    for herb, amount in target_composition.items():
        adjusted_target_composition[herb] = amount * input_dosage
    return adjusted_target_composition


def search(name, database, target_composition, penalty_factor, top_n):
    best_matches, elapsed = searcher.find_best_matches(name, database, target_composition, penalty_factor, top_n)

    print(f'計算匹配度用時: {elapsed}')

    for match in best_matches:
        match_percentage, combination, dosages = match

        combined_composition = herbs_amount = {}
        for dosage, formula in zip(dosages, combination):
            for herb, amount in database[formula].items():
                if herb in herbs_amount:
                    herbs_amount[herb] += amount * dosage
                else:
                    herbs_amount[herb] = amount * dosage

        herbs_amount = dict(sorted(herbs_amount.items(), key=lambda item: (item[0] not in target_composition, item[0])))
        herbs_amount = {f'**{herb}**' if herb in target_composition else herb: amount for herb, amount in herbs_amount.items()}

        missing_herbs = {herb: target_composition.get(herb, 0) - combined_composition.get(herb, 0) for herb in target_composition}
        missing_herbs = {herb: amount for herb, amount in missing_herbs.items() if amount > 0}

        combination_str = ', '.join([f'{formula}{dosage:.1f}' for formula, dosage in zip(combination, dosages)])
        print(f'匹配度: {match_percentage:.2f}%，組合: {combination_str}')
        for herb, amount in herbs_amount.items():
            print(f'    {herb}: {amount:.2f}')

        # 收集組合中已出現的藥材
        combined_herbs = set()
        for formula in combination:
            combined_herbs.update(database[formula].keys())

        if missing_herbs:
            print('尚缺藥物：')
            for herb in missing_herbs.keys():
                if missing_herbs[herb] > 0 and herb not in combined_herbs:
                    print(f'    {herb}')
        else:
            print('所有目標藥材已被完全匹配。')
        print('\n')


def cmd_search(args):
    try:
        database = searcher.load_formula_database(args.database)
    except OSError:
        print(f'無法載入資料庫檔案: {args.database}')
        return

    print(f'方劑數量:{len(database.keys())}')

    if not args.items:
        interactive_input(args)

    if len(args.items) > 1:
        adjusted_target_composition = {}
        unknown_herbs = []
        for herb, amount in args.items:
            if not any(herb in herbs for formula in database.values() for herbs in formula):
                unknown_herbs.append(herb)
            else:
                if herb in adjusted_target_composition:
                    adjusted_target_composition[herb] += amount
                else:
                    adjusted_target_composition[herb] = amount
        if unknown_herbs:
            print(f'資料庫尚未收錄以下藥物：{", ".join(unknown_herbs)}')
        else:
            search(None, database, adjusted_target_composition, args.penalty, args.num)
    else:
        formula_name, input_dosage = args.items[0]
        if formula_name in database:
            target_composition = database[formula_name]
            adjusted_target_composition = adjust_target_composition_for_dosage(target_composition, input_dosage)
            search(formula_name, database, adjusted_target_composition, args.penalty, args.num)
        else:
            print('資料庫尚未收錄此方劑。')


def interactive_input(args):
    penalty_factor_input = input(f'請輸入懲罰因子（預設為{args.penalty}）：')
    if penalty_factor_input:
        try:
            args.penalty = float(penalty_factor_input)
        except ValueError:
            print(f'懲罰因子輸入非法，將使用預設值{args.penalty}')

    user_input = input('請輸入方劑名稱和劑量或藥材組合(例如：補中益氣湯3.5或人參3.0+茯苓2.5)：')
    args.items = []
    if '+' in user_input:
        herbs_input = user_input.split('+')
        for herb_input in herbs_input:
            herb, dosage = parse_input_item(herb_input)
            args.items.append((herb, dosage))
    else:
        formula_name, input_dosage = parse_input_item(user_input)
        args.items.append((formula_name, input_dosage))


def parse_item(value):
    name, sep, dose = value.partition(':')
    return name, float(dose)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="""搜尋中藥配方的替代組合。""",
    )
    parser.add_argument(
        '--version', action='version', version=f'{__package__} {__version__}',
        help="""顯示版本資訊並離開""",
    )

    parser.add_argument(
        'items', metavar='NAME:DOSE', nargs='*', type=parse_item, action='store',
        help="""要搜尋的品項及劑量。可輸入一個複方或多個中藥，例如 '補中益氣湯:3.0' 或 '人參:3.0 茯苓:2.5'""",
    )
    parser.add_argument(
        '-p', '--penalty', metavar='FACTOR', default=2.0, type=float, action='store',
        help="""未配對項目的懲罰因子 (預設: %(default)s)""",
    )
    parser.add_argument(
        '-n', '--num', metavar='N', default=5, type=int, action='store',
        help="""最佳匹配結果顯示筆數 (預設: %(default)s)""",
    )
    parser.add_argument(
        '-d', '--database', metavar='FILE', default=searcher.DEFAULT_DATAFILE, action='store',
        help="""使用自訂的資料庫檔案 (預設: %(default)s)""",
    )

    return parser.parse_args(argv)


def main():
    args = parse_args()
    cmd_search(args)
