document.addEventListener('DOMContentLoaded', function() {
    
    const avatarPreview = document.getElementById('avatarPreview');
    const previewImg = document.getElementById('previewImg');
    const colorBtns = document.querySelectorAll('.color-btn');
    const charItems = document.querySelectorAll('.char-item');


    colorBtns.forEach(btn => {
        btn.addEventListener('click', function() {

            colorBtns.forEach(b => b.classList.remove('active'));
            
            this.classList.add('active');

            const newColor = this.getAttribute('data-color');

            avatarPreview.className = 'avatar-preview';
            avatarPreview.classList.add(newColor);
        });
    });

    charItems.forEach(item => {
        item.addEventListener('click', function() {

            charItems.forEach(i => i.classList.remove('active'));
            
            this.classList.add('active');

            const newImgSrc = this.querySelector('img').getAttribute('src');
            
            previewImg.setAttribute('src', newImgSrc);
        });
    });

});