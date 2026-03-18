import { useEffect, useState } from "react";

const year = 2026;

function Slide({ children }) {
  return (
    <div
      style={{
        height: "100vh",
        width: "100vw",
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        background: "black",
        color: "white",
      }}
    >
      {children}
    </div>
  );
}

export default function App() {
  const [data, setData] = useState(null);
  const [index, setIndex] = useState(0);

  useEffect(() => {
    fetch(`http://localhost:8090/api/recap/${year}`)
      .then((res) => res.json())
      .then(setData);
  }, []);

  useEffect(() => {
    const interval = setInterval(() => {
      setIndex((prev) => (prev + 1) % 6);
    }, 3000);

    return () => clearInterval(interval);
  }, []);

  if (!data) return <div>Loading...</div>;

  const slides = [
    <Slide>
      <h1>Your {year} Recap</h1>
    </Slide>,
    <Slide>
      <h1>{Math.round(data.total_hours)} hours</h1>
      <p>watched this year</p>
    </Slide>,
    <Slide>
      <h1>{data.top_movies?.[0]?.title || "No data"}</h1>
      <p>top movie</p>
    </Slide>,
    <Slide>
      <h1>{data.top_shows?.[0]?.title || "No data"}</h1>
      <p>top show</p>
    </Slide>,
    <Slide>
      <h1>{data.most_active_day}</h1>
      <p>most active day</p>
    </Slide>,
    <Slide>
      <h1>That’s your year</h1>
    </Slide>,
  ];

  return slides[index];
}
