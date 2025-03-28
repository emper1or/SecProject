document.addEventListener('DOMContentLoaded', function () {
    const togglePassword = document.getElementById('togglePassword');

    if (togglePassword) {
        togglePassword.addEventListener('click', function () {
            const passwordInput = document.getElementById('password');
            const icon = this.querySelector('i');

            // Переключаем тип поля ввода
            const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
            passwordInput.setAttribute('type', type);

            // Переключаем иконку
            icon.classList.toggle('fa-eye');
            icon.classList.toggle('fa-eye-slash');

            // Добавляем/убираем зачеркивание
            icon.style.textDecoration = icon.classList.contains('fa-eye-slash') ? 'line-through' : 'none';
        });
    }
});