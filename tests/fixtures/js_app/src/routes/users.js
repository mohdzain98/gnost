const router = require('express').Router();

function list(req, res) {
  res.json([]);
}

router.get('/', list);
router.post(
  '/:id',
  auth,
  (req, res) => res.sendStatus(204),
);

module.exports = router;
