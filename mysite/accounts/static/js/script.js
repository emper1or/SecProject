document.addEventListener('DOMContentLoaded', function () {
    // Находим элемент "глазика"
    const togglePassword = document.getElementById('togglePassword');

    // Добавляем обработчик события на клик
    if (togglePassword) {
        togglePassword.addEventListener('click', function () {
            const passwordInput = document.getElementById('password');
            const icon = this.querySelector('i');

            this.classList.toggle('fa-eye');
            this.classList.toggle('fa-eye-slash');
        });
    }
});