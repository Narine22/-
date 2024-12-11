import sys
import pandas as pd
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QPushButton, QVBoxLayout, QWidget, QDialog,
    QFormLayout, QLineEdit, QComboBox, QMessageBox, QTableWidgetItem, QTableWidget)
from PyQt6.QtCore import Qt
import sqlite3
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np
from pyqtgraph import TableWidget
from PyQt6.QtWidgets import QFileDialog

class FinanceApp:
    def __init__(self):
        self.db_conn = sqlite3.connect('finance.db')
        self.create_tables()
        self.show_login()

    def create_tables(self):
        cursor = self.db_conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS expenses (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                month TEXT NOT NULL,
                category TEXT NOT NULL,
                amount REAL NOT NULL,
                note TEXT,
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        self.db_conn.commit()

    def show_login(self):
        self.login_window = LoginWindow(self)
        self.login_window.show()

    def show_main(self, user_id):
        self.main_window = MainWindow(self, user_id)
        self.main_window.show()

    def register_user(self, username, password):
        cursor = self.db_conn.cursor()
        cursor.execute('SELECT id FROM users WHERE username = ?', (username,))
        existing_user = cursor.fetchone()

        if existing_user:
            return False  # User with this username already exists

        cursor.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password))
        self.db_conn.commit()
        return True  # Registration successful

    def authenticate(self, username, password):
        cursor = self.db_conn.cursor()
        cursor.execute('SELECT id FROM users WHERE username = ? AND password = ?', (username, password))
        user = cursor.fetchone()

        if user:
            return user[0]  # Return user ID if authentication successful
        else:
            return None  # Return None if authentication failed

    def add_expense(self, user_id, month, category, amount, note):
        try:
            amount = float(amount)  # Преобразуем строку в число
            amount = round(amount, 2)  # Округляем до двух знаков после запятой
        except ValueError:
            raise ValueError("Invalid amount format")  # Обработка ошибки

        cursor = self.db_conn.cursor()
        cursor.execute('''
            INSERT INTO expenses (user_id, month, category, amount, note)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, month, category, amount, note))
        self.db_conn.commit()
        self.main_window.update_data()
    def edit_expense(self, expense_id, month, category, amount, note):
        amount = round(float(amount), 2)  # Округляем до двух знаков после запятой
        cursor = self.db_conn.cursor()
        cursor.execute('''
            UPDATE expenses
            SET month = ?, category = ?, amount = ?, note = ?
            WHERE id = ?
        ''', (month, category, amount, note, expense_id))
        self.db_conn.commit()
        self.main_window.update_data()

    def delete_expense(self, expense_id):
        cursor = self.db_conn.cursor()
        cursor.execute('DELETE FROM expenses WHERE id = ?', (expense_id,))
        self.db_conn.commit()
        self.main_window.update_data()

    def get_expenses(self, user_id, month=None):
        cursor = self.db_conn.cursor()
        if month:
            cursor.execute('''
                SELECT id, month, category, amount, note FROM expenses
                WHERE user_id = ? AND month = ?
            ''', (user_id, month))
        else:
            cursor.execute('''
                SELECT id, month, category, amount, note FROM expenses
                WHERE user_id = ?
            ''', (user_id,))

        expenses = cursor.fetchall()
        # Преобразуем значения amount в float и округляем
        for i in range(len(expenses)):
            expenses[i] = (
            expenses[i][0], expenses[i][1], expenses[i][2], round(float(expenses[i][3]), 2), expenses[i][4])

        return expenses

    def get_expense_data(self, expense_id):
        cursor = self.db_conn.cursor()
        cursor.execute('SELECT month, category, amount, note FROM expenses WHERE id = ?', (expense_id,))
        return cursor.fetchone()


class LoginWindow(QMainWindow):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setWindowTitle("Авторизация")
        self.setGeometry(100, 100, 400, 250)  # Увеличиваем высоту окна

        layout = QVBoxLayout()

        self.username_label = QLabel("Логин пользователя или имя:")
        self.username_entry = QLineEdit()
        self.password_label = QLabel("Пароль:")
        self.password_entry = QLineEdit()
        self.password_entry.setEchoMode(QLineEdit.EchoMode.Password)

        login_button = QPushButton("Войти")
        login_button.clicked.connect(self.login)

        admin_login_button = QPushButton("Войти как администратор")
        admin_login_button.clicked.connect(self.login_as_admin)

        register_button = QPushButton("Зарегистрироваться")
        register_button.clicked.connect(self.show_register)

        layout.addWidget(self.username_label)
        layout.addWidget(self.username_entry)
        layout.addWidget(self.password_label)
        layout.addWidget(self.password_entry)
        layout.addWidget(login_button)
        layout.addWidget(admin_login_button)  # Добавляем кнопку для входа как администратор
        layout.addWidget(register_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def login(self):
        username = self.username_entry.text()
        password = self.password_entry.text()
        user_id = self.app.authenticate(username, password)

        if user_id is not None:
            self.app.show_main(user_id)
            self.close()
        else:
            QMessageBox.warning(self, 'Не удалось войти.', 'Неправильный логин или пароль.')

    def login_as_admin(self):
        username = self.username_entry.text()
        password = self.password_entry.text()

        if username == "admin" and password == "admin_password":  # учетные данные
            QMessageBox.information(self, 'Успех', 'Вы вошли как администратор.')
            # Здесь вы можете открыть окно администратора или выполнить другие действия
            self.close()  # Закрываем окно входа
        else:
            QMessageBox.warning(self, 'Не удалось войти.', 'Неправильный логин или пароль администратора.')

    def show_register(self):
        register_dialog = RegisterDialog(self.app, self)
        register_dialog.exec()
class RegisterDialog(QDialog):
    def __init__(self, finance_app, login_window):
        super().__init__()
        self.finance_app = finance_app
        self.login_window = login_window
        self.setWindowTitle("Регистрация")

        layout = QFormLayout()

        self.username_entry = QLineEdit()
        self.password_entry = QLineEdit()
        self.password_entry.setEchoMode(QLineEdit.EchoMode.Password)

        register_button = QPushButton("Зарегистрироваться")
        register_button.clicked.connect(self.register)

        layout.addRow("Имя пользователя или логин:", self.username_entry)
        layout.addRow("Пароль:", self.password_entry)
        layout.addRow(register_button)

        self.setLayout(layout)

    def register(self):
        username = self.username_entry.text()
        password = self.password_entry.text()

        if not username or not password:
            QMessageBox.warning(self, 'Регистрация провалена', 'Пожалуйста, введите как имя пользователя, так и пароль.')
            return

        if self.finance_app.register_user(username, password):
            QMessageBox.information(self, 'Регистрация прошла успешно',
                                    'Учетная запись успешно создана. Теперь вы можете войти в систему.')
            self.accept()
        else:
            QMessageBox.warning(self, "Ошибка регистрации", "Имя пользователя уже существует. Пожалуйста, выберите другое имя пользователя.")


class MainWindow(QMainWindow):
    def __init__(self, app, user_id):
        super().__init__()
        self.app = app
        self.user_id = user_id
        self.selected_month = None
        self.setWindowTitle("FinanceBook")
        self.setGeometry(100, 100, 800, 600)

        layout = QVBoxLayout()

        add_expense_button = QPushButton("Добавить расход")
        add_expense_button.clicked.connect(self.show_add_expense)
        layout.addWidget(add_expense_button)

        # Добавляем кнопку для экспорта в Excel
        export_button = QPushButton("Экспортировать в Excel")
        export_button.clicked.connect(self.export_to_excel)
        layout.addWidget(export_button)

        self.chart_canvas = MatplotlibCanvas(self, width=5, height=4, dpi=100)
        layout.addWidget(self.chart_canvas)

        self.expense_list_widget = TableWidget()
        layout.addWidget(self.expense_list_widget)

        edit_expense_button = QPushButton("Редактировать расход")
        edit_expense_button.clicked.connect(self.edit_selected_expense)
        layout.addWidget(edit_expense_button)

        delete_expense_button = QPushButton("Удалить расход")
        delete_expense_button.clicked.connect(self.delete_selected_expense)
        layout.addWidget(delete_expense_button)

        update_chart_button = QPushButton("Обновить диаграмму")
        update_chart_button.clicked.connect(self.update_chart)
        layout.addWidget(update_chart_button)

        # Внутри __init__ метода класса MainWindow
        self.month_filter_combobox = QComboBox()
        self.month_filter_combobox.addItems(["Все"] + ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"])
        self.month_filter_combobox.currentIndexChanged.connect(self.filter_expenses_by_month)
        layout.addWidget(self.month_filter_combobox)

        self.total_expense_label = QLabel("Общая Сумма расходов: ")
        layout.addWidget(self.total_expense_label)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.monthly_expense_label = QLabel("Сумма расходов за месяц: ")
        layout.addWidget(self.monthly_expense_label)

        self.update_data()

    def export_to_excel(self):
        expenses = self.app.get_expenses(self.user_id)
        if not expenses:
            QMessageBox.warning(self, "Нет данных", "Нет расходов для экспорта.")
            return

        # Создаем DataFrame из данных о расходах
        df = pd.DataFrame(expenses, columns=["ID", "Месяц", "Категория", "Сумма", "Заметка"])
        df['Сумма'] = df['Сумма'].apply(lambda x: round(x, 2))  # Округляем суммы
        # Сохраняем в Excel файл
        file_name, _ = QFileDialog.getSaveFileName(self, "Сохранить файл", "", "Excel Files (*.xlsx)")
        if file_name:
            df.to_excel(file_name, index=False)
            QMessageBox.information(self, "Успех", "Данные успешно экспортированы в Excel.")

    def update_data(self):
        self.update_chart()
        self.update_expense_list()
        self.update_monthly_expense()
        self.update_total_expense()

        # Код для фильтрации списка расходов по месяцу
        selected_month_index = self.month_filter_combobox.currentIndex()
        if selected_month_index > 0:  # Если выбран конкретный месяц
            selected_month = self.month_filter_combobox.currentText()
            expense_table_data = self.get_expense_table_data(month=selected_month)
        else:  # Если выбран пункт "Все"
            expense_table_data = self.get_expense_table_data()

        # Сумма расходов в отфильтрованном или общем списке
        total_expense = sum(float(expense[3]) for expense in expense_table_data[1] if
                            isinstance(expense[3], (str, float)) and str(expense[3]).replace('.', '', 1).isdigit())

        # Обновление текста лейбла с общей суммой расходов
        self.total_expense_label.setText(f"Общая Сумма расходов: {total_expense:.2f}")

        # Форматирование сумм в expense_table_data[1] перед обновлением виджета
        formatted_expenses = []
        for expense in expense_table_data[1]:
            formatted_expense = list(expense)  # Копируем данные о расходе
            formatted_expense[3] = f"{float(expense[3]):.2f}"  # Форматируем сумму с 2 знаками после запятой
            formatted_expenses.append(formatted_expense)

        # Обновление данных в таблице расходов
        self.expense_list_widget.setData(formatted_expenses)
    def update_chart(self):
        expenses = self.app.get_expenses(self.user_id, month=self.selected_month)
        if expenses:
            series_dict = {}

            for data in expenses:
                category = data[2]
                amount = data[3]

                try:
                    amount = float(amount)
                except ValueError:
                    continue

                if not np.isnan(amount):
                    if category in series_dict:
                        series_dict[category] += amount
                    else:
                        series_dict[category] = amount

            if series_dict:
                labels = list(series_dict.keys())
                sizes = list(series_dict.values())

                self.chart_canvas.update_pie_chart(labels, sizes)
                self.chart_canvas.show()
            else:
                self.chart_canvas.hide()
        else:
            self.chart_canvas.hide()

    def calculate_total_expense(self, month=None):
        # Получаем список расходов
        expenses = self.app.get_expenses(self.user_id, month=month)
        # Проверяем, есть ли расходы
        if not expenses:
            return 0.00  # Возвращаем 0, если нет расходов

        total = 0.00  # Инициализируем переменную для накопления суммы
        # Проходим по всем расходам и суммируем
        for expense in expenses:
            amount = expense[3]
            if amount is not None and isinstance(amount, (str, float)):
                try:
                    value = float(amount)  # Преобразуем значение в float
                    total += value  # Добавляем значение к total
                except (ValueError, TypeError):
                    # Можно добавить обработку ошибки, если это необходимо
                    pass  # Игнорируем ошибку

        total = round(total, 2)  # Округляем общую сумму до двух знаков после запятой
        return total  # Возвращаем общую сумму

    def update_monthly_expense(self):
        if self.selected_month:
            monthly_expense = self.calculate_total_expense(month=self.selected_month)
            self.monthly_expense_label.setText(f"Сумма расходов за {self.selected_month}: {monthly_expense:.2f}")
        else:
            self.monthly_expense_label.clear()

    def update_total_expense(self):
        total_expense = self.calculate_total_expense()  # Получаем общую сумму расходов
        if total_expense is not None:
            self.total_expense_label.setText(f"Общая сумма расходов: {total_expense:.2f}")  # Обновляем текст метки
        else:
            self.total_expense_label.setText("Ошибка при расчете общей суммы расходов.")  # Сообщаем об ошибке

    def show_add_expense(self):
        add_expense_dialog = AddExpenseDialog(self)
        add_expense_dialog.exec()
        self.update_data()

    def edit_selected_expense(self):
        selected_rows = self.expense_list_widget.selectedItems()
        if selected_rows:
            expense_id = selected_rows[0].text()
            edit_expense_dialog = EditExpenseDialog(self, expense_id)
            edit_expense_dialog.exec()
            self.update_data()

    def filter_expenses_by_month(self, index):
        selected_month = self.month_filter_combobox.currentText()
        self.selected_month = selected_month if selected_month != "Все" else None
        self.update_data()

    def delete_selected_expense(self):
        selected_rows = self.expense_list_widget.selectedItems()
        if selected_rows:
            expense_id = int(selected_rows[0].text())
            response = QMessageBox.question(
                self, 'Подтверждение удаления', 'Вы уверены, что хотите удалить этот расход?',
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, QMessageBox.StandardButton.No)

            if response == QMessageBox.StandardButton.Yes:
                self.app.delete_expense(expense_id)
                self.update_data()

    def update_expense_list(self):
        header, data = self.get_expense_table_data()
        data = data[1:]  # Убедитесь, что это правильно
        self.expense_list_widget.setData(data)

        total_expense = sum(float(expense[3]) for expense in data if
                            isinstance(expense[3], (str, float)) and str(expense[3]).replace('.', '', 1).isdigit())

        self.total_expense_label.setText(f"Общая Сумма расходов: {total_expense:.2f}")

    def get_expense_table_data(self, month=None):
        header = ["ID", "Месяц", "Категория", "Сумма", "Заметка"]
        data = self.app.get_expenses(self.user_id, month=month)

        # Форматируем суммы
        formatted_data = []
        for expense in data:
            formatted_expense = (
                expense[0],  # ID
                expense[1],  # Месяц
                expense[2],  # Категория
                f"{expense[3]:.2f}",  # Форматируем сумму
                expense[4]  # Заметка
            )
            formatted_data.append(formatted_expense)

        return header, formatted_data

class TableWidget(QTableWidget):
    def setData(self, data):
        self.clearContents()  # Очищаем содержимое таблицы
        if not data or not data[0]:
            return  # Нет данных для отображения
        self.setRowCount(len(data))
        self.setColumnCount(len(data[0]))

        for i, row in enumerate(data):
            for j, item in enumerate(row):
                if j == 3:  # Индекс столбца "Сумма"
                    item = round(float(item), 2)  # Округляем сумму
                self.setItem(i, j, QTableWidgetItem(str(item)))



class MatplotlibCanvas(FigureCanvas):
    def __init__(self, parent=None, width=5, height=4, dpi=100):
        self.fig, self.ax = plt.subplots(figsize=(width, height), dpi=dpi)
        FigureCanvas.__init__(self, self.fig)
        self.setParent(parent)
        self.clear_chart()

    def update_pie_chart(self, labels, sizes):
        self.clear_chart()
        if sum(sizes) == 0:
            sizes = [1] * len(labels)
        self.ax.pie(sizes, labels=labels, autopct='%1.1f%%', startangle=90)
        self.draw()

    def clear_chart(self):
        self.ax.clear()
        self.ax.set_facecolor('#f0f0f0')
        self.draw()

class EditExpenseDialog(QDialog):
    def __init__(self, main_window, expense_id):
        super().__init__()
        self.main_window = main_window
        self.expense_id = expense_id
        self.setWindowTitle("Редактировать расход")

        # Получение данных о расходе
        expense_data = self.main_window.app.get_expense_data(self.expense_id)

        layout = QFormLayout()

        self.month_combobox = QComboBox()
        self.month_combobox.addItems(
            ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"])
        self.category_combobox = QComboBox()
        self.category_combobox.addItems(["Еда", "Транспорт", "Развлечения", "Жилье", "Медицина", "Одежда", "Красота", "Путешествия", "Образование", "Спорт", "Другое"])
        self.amount_entry = QLineEdit()
        self.note_entry = QLineEdit()

        # Установка текущих значений
        self.month_combobox.setCurrentText(expense_data[0])
        self.category_combobox.setCurrentText(expense_data[1])
        self.amount_entry.setText(str(expense_data[2]))
        self.note_entry.setText(expense_data[3])

        save_button = QPushButton("Сохранить изменения")
        save_button.clicked.connect(self.save_expense)

        layout.addRow("Месяц:", self.month_combobox)
        layout.addRow("Категория:", self.category_combobox)
        layout.addRow("Сумма:", self.amount_entry)
        layout.addRow("Заметка:", self.note_entry)
        layout.addRow(save_button)

        self.setLayout(layout)

    def save_expense(self):
        month = self.month_combobox.currentText()
        category = self.category_combobox.currentText()
        amount_text = self.amount_entry.text()
        note = self.note_entry.text()

        try:
            amount = float(amount_text)
            amount = round(amount, 2)  # Округляем до двух знаков после запятой
        except ValueError:
            QMessageBox.warning(self, 'Неверная сумма', 'Пожалуйста, введите корректную числовую сумму.')
            return

        self.main_window.app.add_expense(self.main_window.user_id, month, category, amount, note)
        self.accept()


class AddExpenseDialog(QDialog):
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setWindowTitle("Добавить расход")

        layout = QFormLayout()

        # Комбобоксы для выбора месяца и категории
        self.month_combobox = QComboBox()
        self.month_combobox.addItems(
            ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь", "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь",
             "Декабрь"])

        self.category_combobox = QComboBox()
        self.category_combobox.addItems(
            ["Еда", "Транспорт", "Развлечения", "Жилье", "Медицина", "Одежда", "Красота", "Путешествия", "Образование",
             "Спорт", "Другое"])

        # Поле для ввода суммы с валидатором
        self.amount_entry = QLineEdit()
        self.note_entry = QLineEdit()

        # Кнопка для сохранения расхода
        save_button = QPushButton("Сохранить расход")
        save_button.clicked.connect(self.save_expense)

        # Добавляем элементы в макет
        layout.addRow("Месяц:", self.month_combobox)
        layout.addRow("Категория:", self.category_combobox)
        layout.addRow("Сумма:", self.amount_entry)
        layout.addRow("Заметка:", self.note_entry)
        layout.addRow(save_button)

        self.setLayout(layout)

    def save_expense(self):
        month = self.month_combobox.currentText()
        category = self.category_combobox.currentText()
        amount_text = self.amount_entry.text()
        note = self.note_entry.text()

        try:
            amount = float(amount_text)
            amount = round(amount, 2)  # Округляем до двух знаков после запятой
        except ValueError:
            QMessageBox.warning(self, 'Неверная сумма', 'Пожалуйста, введите корректную числовую сумму.')
            return

        # Сохранение расхода через основной интерфейс
        self.main_window.app.add_expense(self.main_window.user_id, month, category, amount, note)
        self.accept()

if __name__ == '__main__':
    app = QApplication(sys.argv)
    finance_app = FinanceApp()  # Предполагается, что у вас есть класс FinanceApp
    sys.exit(app.exec())