import React from 'react';
import { useMediaQuery } from '../../hooks/useMediaQuery';
import './Layout.css';

const MOBILE_BREAKPOINT = 768;

export interface LayoutProps {
  avatarArea: React.ReactNode;
  textArea: React.ReactNode;
}

export const Layout: React.FC<LayoutProps> = ({ avatarArea, textArea }) => {
  const isMobile = useMediaQuery(MOBILE_BREAKPOINT);

  return (
    <div className={`layout ${isMobile ? 'mobile' : 'desktop'}`}>
      <div className="avatar-section">{avatarArea}</div>
      <div className="text-section">{textArea}</div>
    </div>
  );
};
