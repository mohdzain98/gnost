import { lazy } from 'react';
import {
  Button,
  type ButtonProps,
} from '@/components/ui/button';
import { useThing } from '@/hooks/useThing';
import schema from '@/lib/schema.json?raw';

const Home = lazy(() => import('@/pages/Home'));
const About = lazy(() => import('./pages/About'));

export default function App() {
  useThing();
  return <div><Home /><About /><Button /></div>;
}
