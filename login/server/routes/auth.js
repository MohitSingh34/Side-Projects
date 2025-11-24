const express = require('express');
const router = express.Router();

// In-memory user storage
const users = [];

router.post('/register', (req, res) => {
  const { email, password } = req.body;

  if (!email || !password) {
    return res.status(400).json({ message: 'Email and password are required' });
  }

  const existingUser = users.find(u => u.email === email);
  if (existingUser) {
    return res.status(400).json({ message: 'User already exists' });
  }

  const newUser = { id: Date.now(), email, password };
  users.push(newUser);

  res.status(201).json({ message: 'User registered successfully' });
});

router.post('/login', (req, res) => {
  const { email, password } = req.body;

  if (!email || !password) {
    return res.status(400).json({ message: 'Email and password are required' });
  }

  const user = users.find(u => u.email === email && u.password === password);
  if (!user) {
    return res.status(401).json({ message: 'Invalid credentials' });
  }

  res.status(200).json({ message: 'Login successful', user: { id: user.id, email: user.email } });
});

module.exports = router;
