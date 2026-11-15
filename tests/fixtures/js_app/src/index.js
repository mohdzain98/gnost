const express = require('express');
import { greet } from './lib/greet';
const usersRouter = require('./routes/users');
const app = express();
app.get('/', (req, res) => res.send(greet()));
app.use('/api/users', usersRouter);
app.listen(3000);
