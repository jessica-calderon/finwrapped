import Slide from "./Slide.jsx";

export default function RecapSlides({
  slides,
  activeIndex,
  activeSlide,
  onAdvance,
  onPrevious,
}) {
  return (
    <section className="wrapped-stage" aria-label="Wrapped recap">
      <div className="wrapped-progress" aria-hidden="true">
        {slides.map((slide, slideIndex) => (
          <span
            key={slide.id || slide.title || slideIndex}
            className={`wrapped-progress-dot ${
              slideIndex === activeIndex ? "is-active" : ""
            }`}
          />
        ))}
      </div>

      <Slide
        label={activeSlide.label}
        title={activeSlide.title}
        subtitle={activeSlide.subtitle}
        theme={activeSlide.theme}
        onNext={onAdvance}
        onPrevious={slides.length > 1 ? onPrevious : undefined}
      />

      <p className="wrapped-hint">
        Click anywhere to continue
        {slides.length > 1 ? ", or use the left side to go back." : "."}
      </p>
    </section>
  );
}
