

// Ждем, пока весь DOM загрузится
document.addEventListener('DOMContentLoaded', function () {
    // Находим элемент "глазика"
    const togglePassword = document.getElementById('togglePassword');

    // Добавляем обработчик события на клик
    if (togglePassword) {
        togglePassword.addEventListener('click', function () {
            const passwordInput = document.getElementById('password');
            const icon = this.querySelector('i');

            // Переключаем тип поля ввода
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text'; // Показываем пароль
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash'); // Меняем иконку на "глаз закрыт" (перечёркнутый)
            } else {
                passwordInput.type = 'password'; // Скрываем пароль
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye'); // Меняем иконку на "глаз открыт"
            }
        });
    }
});
