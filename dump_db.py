import sqlite3

def dump_database():
    try:
        # Подключаемся к базе данных
        conn = sqlite3.connect('artbot.db')
        cursor = conn.cursor()
        
        # Получаем схему таблицы users
        print("=== Схема таблицы users ===")
        cursor.execute("PRAGMA table_info(users)")
        columns = cursor.fetchall()
        for col in columns:
            col_id, col_name, col_type, col_notnull, col_default, col_pk = col
            print(f"Столбец: {col_name}, Тип: {col_type}, Not Null: {col_notnull}, Default: {col_default}, Primary Key: {col_pk}")
        
        # Получаем все записи из таблицы users
        print("\n=== Записи в таблице users ===")
        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()
        
        if not rows:
            print("Таблица пуста.")
            return
        
        # Выводим заголовки столбцов
        col_names = [description[0] for description in cursor.description]
        print("Столбцы:", col_names)
        
        # Выводим записи с типами данных
        for row in rows:
            print("\nЗапись:")
            for col_name, value in zip(col_names, row):
                print(f"  {col_name}: {value} (тип: {type(value).__name__})")
        
        conn.close()
    except Exception as e:
        print(f"Ошибка: {e}")

if __name__ == "__main__":
    dump_database()