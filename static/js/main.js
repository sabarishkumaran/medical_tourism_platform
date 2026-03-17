// main.js - Global Animations and Interactions

document.addEventListener('DOMContentLoaded', () => {
    // 1. Initialize Lenis (Smooth Scrolling)
    const lenis = new Lenis({
        duration: 1.2,
        easing: (t) => Math.min(1, 1.001 - Math.pow(2, -10 * t)), // https://www.desmos.com/calculator/brs54l4xou
        direction: 'vertical',
        gestureDirection: 'vertical',
        smooth: true,
        mouseMultiplier: 1,
        smoothTouch: false,
        touchMultiplier: 2,
        infinite: false,
    });

    function raf(time) {
        lenis.raf(time);
        requestAnimationFrame(raf);
    }
    requestAnimationFrame(raf);

    // Sync GSAP ScrollTrigger with Lenis
    if (typeof gsap !== 'undefined' && typeof ScrollTrigger !== 'undefined') {
        gsap.registerPlugin(ScrollTrigger);
        
        lenis.on('scroll', ScrollTrigger.update);

        gsap.ticker.add((time) => {
            lenis.raf(time * 1000);
        });

        gsap.ticker.lagSmoothing(0, 0);
    }

    // 2. Global GSAP Interactions
    // Fade Up Animation elements
    const fadeUpElements = document.querySelectorAll('.animate-fade-up');
    fadeUpElements.forEach((el) => {
        gsap.fromTo(el, 
            { y: 50, opacity: 0 }, 
            {
                y: 0,
                opacity: 1,
                duration: 1,
                ease: 'power3.out',
                scrollTrigger: {
                    trigger: el,
                    start: 'top 85%',
                    toggleActions: 'play none none reverse'
                }
            }
        );
    });

    // Parallax background elements
    const parallaxElements = document.querySelectorAll('.parallax-bg');
    parallaxElements.forEach((el) => {
        gsap.to(el, {
            yPercent: 15,
            ease: "none",
            scrollTrigger: {
                trigger: el.parentElement,
                start: "top bottom",
                end: "bottom top",
                scrub: true
            }
        });
    });

    // Staggered reveals for grids (e.g., Hospital Cards)
    const staggeredGrids = document.querySelectorAll('.stagger-grid');
    staggeredGrids.forEach((grid) => {
        const cards = grid.children;
        gsap.fromTo(cards,
            { y: 30, opacity: 0 },
            {
                y: 0,
                opacity: 1,
                duration: 0.8,
                stagger: 0.15,
                ease: "power2.out",
                scrollTrigger: {
                    trigger: grid,
                    start: 'top 80%',
                    toggleActions: 'play none none none'
                }
            }
        );
    });

    // 3. 3D Tilt Effect on Hospital Cards
    const tiltCards = document.querySelectorAll('.tilt-card');
    tiltCards.forEach(card => {
        card.addEventListener('mousemove', e => {
            const rect = card.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            const centerX = rect.width / 2;
            const centerY = rect.height / 2;
            const rotateX = ((y - centerY) / centerY) * -5; // max 5 deg
            const rotateY = ((x - centerX) / centerX) * 5;

            gsap.to(card, {
                rotateX: rotateX,
                rotateY: rotateY,
                transformPerspective: 1000,
                duration: 0.5,
                ease: "power2.out"
            });
        });

        card.addEventListener('mouseleave', () => {
            gsap.to(card, {
                rotateX: 0,
                rotateY: 0,
                duration: 0.7,
                ease: "elastic.out(1, 0.3)"
            });
        });
    });

    // 4. Differentiator Icons Animation
    const diffIcons = document.querySelectorAll('.diff-icon');
    diffIcons.forEach((icon, index) => {
        gsap.to(icon, {
            y: -10,
            duration: 1.5 + (index * 0.2), // create offset timing
            yoyo: true,
            repeat: -1,
            ease: "sine.inOut"
        });
    });
});
