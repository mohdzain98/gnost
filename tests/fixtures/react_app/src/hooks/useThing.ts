import { Hub } from 'aws-amplify';

export const useThing = () => Hub.listen('auth', () => {});
