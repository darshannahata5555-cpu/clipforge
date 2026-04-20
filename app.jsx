  Same pattern as Problem 2 but selectedId starts as null instead of 1.

  import React, { useState } from "react";

  const articles = [
    { id: 1, title: "React 19 Features", category: "Frontend" },
    { id: 2, title: "Node.js Scaling Tips", category: "Backend" },
    { id: 3, title: "Designing Better APIs", category: "System Design" },
  ];

  function ArticleItem({ article, isSelected, onView }) {
    return (
      <div
        onClick={() => onView(article.id)}
        style={{
          border: "1px solid #ddd",
          padding: "10px",
          marginBottom: "10px",
          cursor: "pointer",
          backgroundColor: isSelected ? "#eef4ff" : "white",
        }}
      >
        <h4>{article.title}</h4>
        <p>{article.category}</p>
      </div>
    );
  }

  export default function ViewedArticlesTracker() {
    const [viewedArticleId, setViewedArticleId] = useState(null);

    // TODO 1: derive viewedArticle using .find()
    const viewedArticle = articles.fint(articles=> article.id === viewedArticleId);

    return (
      <div style={{ padding: "20px" }}>
        <h2>Articles</h2>

        <div>
          {articles.map((article) => (
            <ArticleItem
              key={article.id}
              article={article}
              // TODO 2: fix isSelected
              isSelected={article.id === viewedArticleId}
              onView={setViewedArticleId}
            />
          ))}
        </div>

        <div style={{ marginTop: "20px" }}>
          <h3>Recently Viewed</h3>
          {/* TODO 3: show "No article viewed yet" if null, otherwise show title and category */}
          <p>No article viewed yet</p>
        </div>
      </div>
    );
  }
