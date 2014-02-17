from setuptools import setup

def readme():
    with open('README.rst') as f:
        return f.read()

setup(name='mailtree',
      version='0.1',
      description='Turn email archives into a forest of MailTree objects',
      url='http://github.com/pasc/mailtree',
      author='Pascal Hakim',
      author_email='pasc@redellipse.net',
      license='MIT',
      packages=['mailtree'],
      zip_safe=False,

      test_suite='nose.collector',
      tests_require=['nose'],

)

