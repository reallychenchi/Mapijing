import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { AvatarArea } from './AvatarArea';

describe('AvatarArea', () => {
  it('should render avatar image with correct alt text', () => {
    render(
      <AvatarArea
        emotion="default"
        showEarIndicator={false}
        isEarBlinking={false}
      />
    );

    const img = screen.getByAltText('虚拟人头像 - default');
    expect(img).toBeInTheDocument();
  });

  it('should render correct avatar for each emotion', () => {
    const emotions = ['default', 'empathy', 'comfort', 'happy'] as const;

    for (const emotion of emotions) {
      const { unmount } = render(
        <AvatarArea
          emotion={emotion}
          showEarIndicator={false}
          isEarBlinking={false}
        />
      );

      const img = screen.getByAltText(`虚拟人头像 - ${emotion}`);
      expect(img).toHaveAttribute('src', `/assets/avatars/${emotion}.png`);

      unmount();
    }
  });

  it('should show ear indicator when showEarIndicator is true', () => {
    render(
      <AvatarArea
        emotion="default"
        showEarIndicator={true}
        isEarBlinking={false}
      />
    );

    const ear = screen.getByRole('img', { name: '耳朵提示' });
    expect(ear).toBeInTheDocument();
  });

  it('should hide ear indicator when showEarIndicator is false', () => {
    render(
      <AvatarArea
        emotion="default"
        showEarIndicator={false}
        isEarBlinking={false}
      />
    );

    const ear = screen.queryByRole('img', { name: '耳朵提示' });
    expect(ear).not.toBeInTheDocument();
  });

  it('should apply blinking class when isEarBlinking is true', () => {
    render(
      <AvatarArea
        emotion="default"
        showEarIndicator={true}
        isEarBlinking={true}
      />
    );

    const ear = screen.getByRole('img', { name: '耳朵提示' });
    expect(ear).toHaveClass('ear-indicator--blinking');
  });

  it('should not apply blinking class when isEarBlinking is false', () => {
    render(
      <AvatarArea
        emotion="default"
        showEarIndicator={true}
        isEarBlinking={false}
      />
    );

    const ear = screen.getByRole('img', { name: '耳朵提示' });
    expect(ear).not.toHaveClass('ear-indicator--blinking');
  });
});
